"""
Database-Configurable Multi-Intent Handler
Loads multi-intent configuration and chain rules from database
"""

import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
import asyncpg
import redis.asyncio as redis
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseMultiIntentHandler:
    """
    Multi-intent handler that loads configuration from database.
    Supports admin-configurable intent splitting, chaining, and combination.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis,
        intent_classifier=None
    ):
        self.db_pool = db_pool
        self.redis = redis_client
        self.intent_classifier = intent_classifier

        # Cache configuration
        self.config: Dict[str, Any] = {}
        self.chain_rules: List[Dict] = []
        self.last_refresh = None

    async def initialize(self):
        """Load initial configuration from database"""
        await self.refresh_configuration()

        # Set up Redis pub/sub
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe('multi_intent_config_update')

        # Start listener
        asyncio.create_task(self._listen_for_updates())

    async def refresh_configuration(self):
        """Load multi-intent configuration from database"""
        try:
            async with self.db_pool.acquire() as conn:
                # Load global config
                config_row = await conn.fetchrow("""
                    SELECT * FROM multi_intent_config
                    ORDER BY id DESC
                    LIMIT 1
                """)

                if config_row:
                    self.config = dict(config_row)
                else:
                    # Default config if none in database
                    self.config = {
                        'enabled': True,
                        'max_intents_per_query': 3,
                        'separators': [' and ', ' then ', ' also '],
                        'context_preservation': True,
                        'parallel_processing': False,
                        'combination_strategy': 'concatenate',
                        'min_words_per_intent': 2,
                        'context_words_to_preserve': []
                    }

                # Load chain rules
                self.chain_rules = [
                    dict(row) for row in await conn.fetch("""
                        SELECT * FROM intent_chain_rules
                        WHERE enabled = true
                        ORDER BY id
                    """)
                ]

            self.last_refresh = datetime.now()
            logger.info(
                f"Multi-intent config refreshed: "
                f"enabled={self.config.get('enabled')}, "
                f"max_intents={self.config.get('max_intents_per_query')}, "
                f"{len(self.chain_rules)} chain rules"
            )

        except Exception as e:
            logger.error(f"Failed to refresh multi-intent configuration: {e}")

    async def _listen_for_updates(self):
        """Listen for configuration updates"""
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    await self.refresh_configuration()
                except Exception as e:
                    logger.error(f"Failed to process update: {e}")

    async def analyze_query(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Analyze query for multiple intents using database configuration.

        Returns:
            Dict with:
            - has_multiple_intents: bool
            - intent_parts: List of sub-queries
            - chain_match: Optional matched chain rule
            - processing_strategy: 'sequential' or 'parallel'
        """
        if not self.config.get('enabled', True):
            return {
                'has_multiple_intents': False,
                'intent_parts': [query],
                'chain_match': None,
                'processing_strategy': 'sequential'
            }

        # Check for chain rule match first
        chain_match = await self._check_chain_rules(query)
        if chain_match:
            return {
                'has_multiple_intents': True,
                'intent_parts': await self._generate_chain_queries(query, chain_match),
                'chain_match': chain_match,
                'processing_strategy': 'sequential'  # Chains are always sequential
            }

        # Check for multi-intent separators
        separators = self.config.get('separators', [])
        intent_parts = await self._split_query(query, separators)

        if len(intent_parts) > 1:
            # Limit to max configured intents
            max_intents = self.config.get('max_intents_per_query', 3)
            intent_parts = intent_parts[:max_intents]

            return {
                'has_multiple_intents': True,
                'intent_parts': intent_parts,
                'chain_match': None,
                'processing_strategy': (
                    'parallel' if self.config.get('parallel_processing', False)
                    else 'sequential'
                )
            }

        return {
            'has_multiple_intents': False,
            'intent_parts': [query],
            'chain_match': None,
            'processing_strategy': 'sequential'
        }

    async def _check_chain_rules(
        self,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Check if query matches any chain rules"""
        query_lower = query.lower()

        for rule in self.chain_rules:
            trigger_pattern = rule.get('trigger_pattern', '')

            # Check if pattern matches
            if trigger_pattern:
                try:
                    if re.search(trigger_pattern, query_lower):
                        logger.info(f"Query matches chain rule: {rule['name']}")
                        return rule
                except re.error:
                    logger.error(f"Invalid regex in chain rule '{rule['name']}': {trigger_pattern}")

        return None

    async def _generate_chain_queries(
        self,
        original_query: str,
        chain_rule: Dict
    ) -> List[str]:
        """
        Generate queries for a chain rule.
        This could be enhanced to use templates from the database.
        """
        intent_sequence = chain_rule.get('intent_sequence', [])
        queries = []

        # For now, use the original query for context
        # In a more sophisticated implementation, we could have
        # query templates stored with the chain rule
        if chain_rule['name'] == 'Goodnight Routine':
            queries = [
                "turn off all lights",
                "lock all doors",
                "set thermostat to sleep mode"
            ]
        elif chain_rule['name'] == 'Morning Routine':
            queries = [
                "turn on bedroom lights",
                "what's the weather today",
                "start the coffee maker"
            ]
        elif chain_rule['name'] == 'Leaving Home':
            queries = [
                "lock all doors",
                "turn off all lights",
                "set home to away mode"
            ]
        else:
            # Default: use original query for all intents in sequence
            queries = [original_query] * len(intent_sequence)

        return queries

    async def _split_query(
        self,
        query: str,
        separators: List[str]
    ) -> List[str]:
        """Split query into multiple intents based on separators"""
        parts = [query]

        # Split on each separator
        for separator in separators:
            new_parts = []
            for part in parts:
                if separator in part.lower():
                    # Case-insensitive split while preserving original case
                    split_index = part.lower().index(separator)
                    before = part[:split_index]
                    after = part[split_index + len(separator):]

                    if before.strip():
                        new_parts.append(before.strip())
                    if after.strip():
                        new_parts.append(after.strip())
                else:
                    new_parts.append(part)

            parts = new_parts

        # Apply context preservation if enabled
        if self.config.get('context_preservation', True):
            parts = await self._preserve_context(parts)

        # Filter by minimum word count
        min_words = self.config.get('min_words_per_intent', 2)
        valid_parts = [
            p for p in parts
            if len(p.split()) >= min_words
        ]

        return valid_parts if valid_parts else [query]

    async def _preserve_context(
        self,
        intent_parts: List[str]
    ) -> List[str]:
        """
        Preserve context between split intents.
        Adds missing context words from previous parts.
        """
        context_words = self.config.get('context_words_to_preserve', [])

        if not context_words:
            # Default context words if none configured
            context_words = ['lights', 'temperature', 'door', 'lock', 'blinds']

        enhanced_parts = []
        previous_context = set()

        for i, part in enumerate(intent_parts):
            part_lower = part.lower()
            current_context = set()

            # Extract context words from current part
            for word in context_words:
                if word in part_lower:
                    current_context.add(word)

            # If this part is missing context but previous had it
            if i > 0 and not current_context and previous_context:
                # Check if this looks like it needs context
                action_words = ['on', 'off', 'up', 'down', 'open', 'close']
                needs_context = any(word in part_lower for word in action_words)

                if needs_context and previous_context:
                    # Add the most relevant context word
                    context_word = list(previous_context)[0]
                    part = f"{context_word} {part}"

            enhanced_parts.append(part)
            previous_context.update(current_context)

        return enhanced_parts

    async def combine_responses(
        self,
        responses: List[Dict[str, Any]]
    ) -> str:
        """
        Combine multiple intent responses based on configured strategy.

        Args:
            responses: List of response dicts with 'query', 'response', 'intent' keys

        Returns:
            Combined response string
        """
        if not responses:
            return ""

        strategy = self.config.get('combination_strategy', 'concatenate')

        if strategy == 'concatenate':
            # Simple concatenation with connectors
            combined_parts = []

            for i, resp in enumerate(responses):
                response_text = resp.get('response', '').strip()

                if response_text:
                    # Add connector for multiple responses
                    if i > 0:
                        if i == len(responses) - 1:
                            combined_parts.append("Finally,")
                        else:
                            combined_parts.append("Additionally,")

                    combined_parts.append(response_text)

            return " ".join(combined_parts)

        elif strategy == 'summarize':
            # Use LLM to create a coherent summary
            # This would require an LLM call
            return await self._summarize_responses(responses)

        elif strategy == 'hierarchical':
            # Primary response first, then secondary details
            if responses:
                primary = responses[0].get('response', '')
                secondary = [r.get('response', '') for r in responses[1:]]

                if secondary:
                    details = " Also: " + " ".join(secondary)
                    return f"{primary}{details}"
                return primary

        # Default to concatenation
        return " ".join(r.get('response', '') for r in responses)

    async def _summarize_responses(
        self,
        responses: List[Dict]
    ) -> str:
        """Summarize multiple responses using LLM"""
        # This would need LLM integration
        # For now, fallback to concatenation
        return " ".join(r.get('response', '') for r in responses)

    async def process_chain(
        self,
        chain_rule: Dict,
        queries: List[str],
        process_func
    ) -> List[Dict[str, Any]]:
        """
        Process a chain of intents according to rule configuration.

        Args:
            chain_rule: The matched chain rule
            queries: List of queries to process
            process_func: Async function to process each query

        Returns:
            List of response dictionaries
        """
        responses = []
        require_all = chain_rule.get('require_all', False)
        stop_on_error = chain_rule.get('stop_on_error', True)

        for i, query in enumerate(queries):
            try:
                # Process the query
                response = await process_func(query)

                # Check if successful
                if response.get('success', True):
                    responses.append(response)
                else:
                    logger.warning(f"Chain step {i+1} failed: {query}")

                    if stop_on_error:
                        break

                    if require_all:
                        return []  # Chain failed

            except Exception as e:
                logger.error(f"Error processing chain step {i+1}: {e}")

                if stop_on_error:
                    break

                if require_all:
                    return []

        return responses

    async def update_configuration(
        self,
        updates: Dict[str, Any]
    ) -> bool:
        """Update multi-intent configuration via API"""
        try:
            async with self.db_pool.acquire() as conn:
                # Build update query
                set_clauses = []
                params = []
                param_count = 1

                for key, value in updates.items():
                    set_clauses.append(f"{key} = ${param_count}")
                    params.append(json.dumps(value) if isinstance(value, (list, dict)) else value)
                    param_count += 1

                if set_clauses:
                    query = f"""
                        UPDATE multi_intent_config
                        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                    """

                    await conn.execute(query, *params)

                    # Notify about update
                    await self.redis.publish(
                        'multi_intent_config_update',
                        json.dumps({'action': 'refresh', 'timestamp': datetime.now().isoformat()})
                    )

                    # Refresh local config
                    await self.refresh_configuration()

                    return True

        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")

        return False

    async def add_chain_rule(
        self,
        name: str,
        trigger_pattern: str,
        intent_sequence: List[str],
        description: str = None,
        examples: List[str] = None
    ) -> int:
        """Add a new intent chain rule"""
        try:
            async with self.db_pool.acquire() as conn:
                rule_id = await conn.fetchval("""
                    INSERT INTO intent_chain_rules
                    (name, trigger_pattern, intent_sequence, description, examples, enabled)
                    VALUES ($1, $2, $3, $4, $5, true)
                    RETURNING id
                """, name, trigger_pattern, intent_sequence, description, examples)

                # Notify about update
                await self.redis.publish(
                    'multi_intent_config_update',
                    json.dumps({'action': 'refresh', 'table': 'intent_chain_rules'})
                )

                # Refresh local config
                await self.refresh_configuration()

                return rule_id

        except Exception as e:
            logger.error(f"Failed to add chain rule: {e}")
            raise

    async def test_splitting(
        self,
        query: str
    ) -> Dict[str, Any]:
        """Test query splitting with detailed results"""
        result = await self.analyze_query(query)

        # Add debug information
        result['debug'] = {
            'config_enabled': self.config.get('enabled', False),
            'configured_separators': self.config.get('separators', []),
            'max_intents': self.config.get('max_intents_per_query', 3),
            'context_preservation': self.config.get('context_preservation', False),
            'combination_strategy': self.config.get('combination_strategy', 'concatenate'),
            'available_chains': [r['name'] for r in self.chain_rules]
        }

        # If chain matched, add chain details
        if result.get('chain_match'):
            chain = result['chain_match']
            result['chain_details'] = {
                'name': chain['name'],
                'description': chain.get('description'),
                'intent_sequence': chain.get('intent_sequence', []),
                'examples': chain.get('examples', [])
            }

        return result

    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'pubsub'):
            await self.pubsub.unsubscribe()
            await self.pubsub.close()