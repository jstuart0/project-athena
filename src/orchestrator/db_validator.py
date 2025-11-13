"""
Database-Configurable Response Validation System
Loads anti-hallucination rules and cross-validation config from database
"""

import re
import json
import asyncio
import logging
from typing import Tuple, Dict, Any, Optional, List
import httpx
import asyncpg
import redis.asyncio as redis
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseResponseValidator:
    """
    Response validator that loads configuration from database.
    Implements admin-configurable anti-hallucination and cross-validation.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis,
        llm_service_url: str = "http://localhost:11434"
    ):
        self.db_pool = db_pool
        self.redis = redis_client
        self.llm_service_url = llm_service_url
        self.client = httpx.AsyncClient(timeout=30.0)

        # Cache configuration
        self.hallucination_checks: List[Dict] = []
        self.cross_validation_models: List[Dict] = []
        self.confidence_rules: Dict[str, List[Dict]] = {}
        self.last_refresh = None

    async def initialize(self):
        """Load initial configuration from database"""
        await self.refresh_configuration()

        # Set up Redis pub/sub for real-time updates
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe('validation_config_update')

        # Start background tasks
        asyncio.create_task(self._listen_for_updates())

    async def refresh_configuration(self):
        """Load validation configuration from database"""
        try:
            async with self.db_pool.acquire() as conn:
                # Load hallucination checks
                self.hallucination_checks = [
                    dict(row) for row in await conn.fetch("""
                        SELECT * FROM hallucination_checks
                        WHERE enabled = true
                        ORDER BY priority DESC, severity DESC
                    """)
                ]

                # Load cross-validation models
                self.cross_validation_models = [
                    dict(row) for row in await conn.fetch("""
                        SELECT * FROM cross_validation_models
                        WHERE enabled = true
                        ORDER BY model_type, weight DESC
                    """)
                ]

                # Load confidence score rules
                confidence_rules = await conn.fetch("""
                    SELECT r.*, c.name as category_name
                    FROM confidence_score_rules r
                    JOIN intent_categories c ON r.category_id = c.id
                    WHERE r.enabled = true
                    ORDER BY c.name, r.factor_type
                """)

                self.confidence_rules = {}
                for rule in confidence_rules:
                    cat_name = rule['category_name']
                    if cat_name not in self.confidence_rules:
                        self.confidence_rules[cat_name] = []
                    self.confidence_rules[cat_name].append(dict(rule))

            self.last_refresh = datetime.now()
            logger.info(
                f"Validation configuration refreshed: "
                f"{len(self.hallucination_checks)} checks, "
                f"{len(self.cross_validation_models)} models"
            )

        except Exception as e:
            logger.error(f"Failed to refresh validation configuration: {e}")

    async def _listen_for_updates(self):
        """Listen for configuration updates via Redis"""
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    if data.get('action') == 'refresh':
                        await self.refresh_configuration()
                except Exception as e:
                    logger.error(f"Failed to process update: {e}")

    async def validate_response(
        self,
        query: str,
        response: str,
        intent_category: str,
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate response using database-configured rules.

        Returns:
            Tuple of (is_valid, final_response, validation_metadata)
        """
        validation_metadata = {
            'checks_performed': [],
            'cross_validation': {},
            'confidence_adjustments': [],
            'overall_valid': True,
            'final_confidence': 0.0
        }

        query_lower = query.lower()
        metadata = metadata or {}

        # Layer 1: Run hallucination checks
        for check in self.hallucination_checks:
            # Check if this rule applies to the category
            applies_to = check.get('applies_to_categories', [])
            if applies_to and intent_category not in applies_to:
                continue

            check_result = await self._run_hallucination_check(
                check,
                query_lower,
                response,
                intent_category
            )

            validation_metadata['checks_performed'].append(check_result)

            # Handle check failure based on severity
            if not check_result['passed']:
                if check['severity'] == 'error':
                    validation_metadata['overall_valid'] = False

                    # Attempt auto-fix if enabled
                    if check.get('auto_fix_enabled'):
                        fixed_response = await self._attempt_auto_fix(
                            check,
                            query,
                            response
                        )
                        if fixed_response != response:
                            response = fixed_response
                            check_result['auto_fixed'] = True

                elif check['severity'] == 'warning':
                    logger.warning(
                        f"Validation warning for check '{check['name']}': "
                        f"{check_result.get('message')}"
                    )

        # Layer 2: Cross-model validation if required
        if await self._should_cross_validate(intent_category, metadata):
            cross_validation_result = await self._run_cross_validation(
                query,
                response,
                intent_category
            )

            validation_metadata['cross_validation'] = cross_validation_result
            validation_metadata['final_confidence'] = cross_validation_result.get(
                'ensemble_confidence', 0.5
            )

            # Check confidence threshold
            min_confidence = await self._get_min_confidence_for_category(intent_category)
            if validation_metadata['final_confidence'] < min_confidence:
                validation_metadata['overall_valid'] = False

        # Layer 3: Apply confidence score adjustments
        if intent_category in self.confidence_rules:
            confidence_adjustments = await self._apply_confidence_rules(
                intent_category,
                query,
                response,
                metadata
            )

            validation_metadata['confidence_adjustments'] = confidence_adjustments

            # Adjust final confidence
            for adjustment in confidence_adjustments:
                validation_metadata['final_confidence'] = max(
                    0.0,
                    min(1.0, validation_metadata['final_confidence'] + adjustment['value'])
                )

        return (
            validation_metadata['overall_valid'],
            response,
            validation_metadata
        )

    async def _run_hallucination_check(
        self,
        check: Dict,
        query: str,
        response: str,
        category: str
    ) -> Dict[str, Any]:
        """Run a single hallucination check"""
        check_type = check['check_type']
        config = check.get('configuration', {})

        result = {
            'check_name': check['name'],
            'check_type': check_type,
            'passed': True,
            'message': None
        }

        try:
            if check_type == 'required_elements':
                # Check if response contains required elements
                response_lower = response.lower()
                required_patterns = config.get('patterns', [])
                query_patterns = config.get('query_patterns', [])

                # Only check if query matches trigger patterns
                should_check = any(p in query for p in query_patterns)

                if should_check:
                    has_required = False
                    for pattern in required_patterns:
                        if '\\d' in pattern:  # Regex pattern
                            if re.search(pattern, response):
                                has_required = True
                                break
                        else:  # Simple substring
                            if pattern in response_lower:
                                has_required = True
                                break

                    if not has_required:
                        result['passed'] = False
                        result['message'] = check.get(
                            'error_message_template',
                            f"Missing required elements for {check['display_name']}"
                        )

            elif check_type == 'fact_checking':
                # Extract and verify facts
                fact_config = config

                if fact_config.get('check_numbers'):
                    # Extract numbers from both query and response
                    query_numbers = set(re.findall(r'\d+', query))
                    response_numbers = set(re.findall(r'\d+', response))

                    # If query has specific numbers, response should reference them
                    if query_numbers and not query_numbers.intersection(response_numbers):
                        result['passed'] = False
                        result['message'] = "Response numbers don't match query context"

            elif check_type == 'confidence_threshold':
                # This is handled in cross-validation layer
                pass

        except Exception as e:
            logger.error(f"Error running check '{check['name']}': {e}")
            result['error'] = str(e)

        return result

    async def _should_cross_validate(
        self,
        category: str,
        metadata: Dict
    ) -> bool:
        """Determine if cross-validation is needed"""
        # Check if any hallucination check requires it
        for check in self.hallucination_checks:
            if check.get('require_cross_model_validation'):
                applies_to = check.get('applies_to_categories', [])
                if not applies_to or category in applies_to:
                    return True

        # Check confidence threshold
        confidence = metadata.get('confidence', 1.0)
        if confidence < 0.6:
            return True

        # Check if category requires validation
        validation_models = [
            m for m in self.cross_validation_models
            if not m.get('use_for_categories') or category in m.get('use_for_categories', [])
        ]

        return len(validation_models) > 1

    async def _run_cross_validation(
        self,
        query: str,
        response: str,
        category: str
    ) -> Dict[str, Any]:
        """Run cross-model validation using configured models"""
        validation_results = []

        # Get applicable models
        applicable_models = [
            m for m in self.cross_validation_models
            if not m.get('use_for_categories') or category in m.get('use_for_categories', [])
        ]

        # Run validation with each model
        for model in applicable_models:
            if model['model_type'] == 'validation':
                model_result = await self._validate_with_model(
                    model,
                    query,
                    response
                )
                validation_results.append({
                    'model': model['name'],
                    'confidence': model_result['confidence'],
                    'weight': float(model.get('weight', 1.0)),
                    'assessment': model_result.get('assessment')
                })

        # Calculate ensemble confidence
        if validation_results:
            total_weight = sum(r['weight'] for r in validation_results)
            weighted_confidence = sum(
                r['confidence'] * r['weight'] for r in validation_results
            ) / max(total_weight, 1.0)
        else:
            weighted_confidence = 0.7  # Default if no validation models

        return {
            'models_used': len(validation_results),
            'results': validation_results,
            'ensemble_confidence': weighted_confidence
        }

    async def _validate_with_model(
        self,
        model_config: Dict,
        query: str,
        response: str
    ) -> Dict[str, Any]:
        """Validate response with a specific model"""
        try:
            validation_prompt = f"""
            Validate this response for accuracy and appropriateness:

            Query: {query}
            Response: {response}

            Provide:
            1. Confidence score (0.0-1.0)
            2. Brief assessment
            3. Any issues found

            Format: CONFIDENCE: X.X | ASSESSMENT: <text> | ISSUES: <text or none>
            """

            # Call validation model
            endpoint = model_config.get('endpoint_url', self.llm_service_url)
            result = await self.client.post(
                f"{endpoint}/api/generate",
                json={
                    "model": model_config['model_id'],
                    "prompt": validation_prompt,
                    "temperature": float(model_config.get('temperature', 0.1)),
                    "max_tokens": model_config.get('max_tokens', 200),
                    "stream": False
                },
                timeout=model_config.get('timeout_seconds', 30)
            )

            if result.status_code == 200:
                response_text = result.json().get('response', '')

                # Parse response
                confidence = 0.5  # Default
                assessment = ""
                issues = ""

                confidence_match = re.search(r'CONFIDENCE:\s*(\d\.\d+)', response_text)
                if confidence_match:
                    confidence = float(confidence_match.group(1))

                assessment_match = re.search(r'ASSESSMENT:\s*([^|]+)', response_text)
                if assessment_match:
                    assessment = assessment_match.group(1).strip()

                issues_match = re.search(r'ISSUES:\s*(.+)', response_text)
                if issues_match:
                    issues = issues_match.group(1).strip()

                return {
                    'confidence': confidence,
                    'assessment': assessment,
                    'issues': issues if issues and issues.lower() != 'none' else None
                }

        except Exception as e:
            logger.error(f"Validation with model '{model_config['name']}' failed: {e}")
            return {
                'confidence': 0.5,
                'assessment': 'Validation error',
                'error': str(e)
            }

        return {'confidence': 0.5, 'assessment': 'Default'}

    async def _attempt_auto_fix(
        self,
        check: Dict,
        query: str,
        response: str
    ) -> str:
        """Attempt to automatically fix a failed response"""
        if not check.get('auto_fix_enabled'):
            return response

        prompt_template = check.get(
            'auto_fix_prompt_template',
            "Fix this response to address the issue: {error_message}\n\nQuery: {query}\nResponse: {response}"
        )

        fix_prompt = prompt_template.format(
            error_message=check.get('error_message_template', 'Validation failed'),
            query=query,
            response=response
        )

        try:
            # Get primary model for fixing
            primary_model = next(
                (m for m in self.cross_validation_models if m['model_type'] == 'primary'),
                None
            )

            if not primary_model:
                return response

            result = await self.client.post(
                f"{self.llm_service_url}/api/generate",
                json={
                    "model": primary_model['model_id'],
                    "prompt": fix_prompt,
                    "temperature": 0.3,
                    "stream": False
                }
            )

            if result.status_code == 200:
                fixed = result.json().get('response', response)
                logger.info(f"Auto-fixed response for check '{check['name']}'")
                return fixed

        except Exception as e:
            logger.error(f"Auto-fix failed for check '{check['name']}': {e}")

        return response

    async def _apply_confidence_rules(
        self,
        category: str,
        query: str,
        response: str,
        metadata: Dict
    ) -> List[Dict[str, Any]]:
        """Apply confidence score adjustment rules"""
        adjustments = []

        if category not in self.confidence_rules:
            return adjustments

        for rule in self.confidence_rules[category]:
            try:
                factor_name = rule['factor_name']
                factor_type = rule['factor_type']
                condition = rule.get('condition', {})
                adjustment_value = float(rule['adjustment_value'])
                max_impact = float(rule.get('max_impact', 0.2))

                should_apply = False
                actual_adjustment = 0.0

                # Check different factor types
                if factor_name == 'pattern_match_count':
                    # Based on number of pattern matches
                    match_count = len(metadata.get('matched_patterns', []))
                    min_matches = condition.get('min_matches', 1)

                    if match_count >= min_matches:
                        should_apply = True
                        # Scale adjustment based on match count
                        actual_adjustment = min(
                            adjustment_value * (match_count / max(min_matches, 1)),
                            max_impact
                        )

                elif factor_name == 'entity_presence':
                    # Based on entity extraction
                    entities = metadata.get('entities', {})
                    required_entities = condition.get('required_entities', [])

                    if all(e in entities for e in required_entities):
                        should_apply = True
                        actual_adjustment = adjustment_value

                elif factor_name == 'query_length':
                    # Based on query complexity
                    word_count = len(query.split())
                    min_words = condition.get('min_words', 5)
                    max_words = condition.get('max_words', 50)

                    if min_words <= word_count <= max_words:
                        should_apply = True
                        actual_adjustment = adjustment_value

                if should_apply:
                    # Apply factor type (boost, penalty, multiplier)
                    if factor_type == 'penalty':
                        actual_adjustment = -abs(actual_adjustment)

                    adjustments.append({
                        'rule': rule['factor_name'],
                        'type': factor_type,
                        'value': actual_adjustment,
                        'reason': f"Applied {factor_name} rule"
                    })

            except Exception as e:
                logger.error(f"Error applying confidence rule: {e}")

        return adjustments

    async def _get_min_confidence_for_category(self, category: str) -> float:
        """Get minimum confidence threshold for a category"""
        async with self.db_pool.acquire() as conn:
            threshold = await conn.fetchval("""
                SELECT confidence_threshold
                FROM intent_categories
                WHERE name = $1
            """, category)

        return float(threshold) if threshold else 0.7

    async def test_validation(
        self,
        test_scenario_id: int
    ) -> Dict[str, Any]:
        """Test validation with a specific scenario from database"""
        async with self.db_pool.acquire() as conn:
            scenario = await conn.fetchrow("""
                SELECT * FROM validation_test_scenarios
                WHERE id = $1
            """, test_scenario_id)

            if not scenario:
                return {'error': 'Test scenario not found'}

            # Run validation
            is_valid, final_response, metadata = await self.validate_response(
                scenario['test_query'],
                scenario['initial_response'],
                scenario['category'],
                {}
            )

            # Check against expected
            result = {
                'scenario': dict(scenario),
                'actual_valid': is_valid,
                'expected_valid': scenario['expected_validation_result'] == 'pass',
                'passed': is_valid == (scenario['expected_validation_result'] == 'pass'),
                'final_response': final_response,
                'metadata': metadata
            }

            # Update test result in database
            await conn.execute("""
                UPDATE validation_test_scenarios
                SET last_run_result = $1, last_run_date = $2
                WHERE id = $3
            """, json.dumps(result), datetime.now(), test_scenario_id)

        return result

    async def close(self):
        """Clean up resources"""
        await self.client.aclose()
        if hasattr(self, 'pubsub'):
            await self.pubsub.unsubscribe()
            await self.pubsub.close()