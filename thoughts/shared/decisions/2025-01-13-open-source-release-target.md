# Architecture Decision: Open Source Release Target

**Date:** 2025-01-13
**Status:** Accepted
**Decision By:** Jay Stuart
**Tags:** architecture, open-source, licensing, documentation, community

---

## Context

Project Athena is being developed as a next-generation AI voice assistant system focused on privacy, local processing, and smart home integration. The project aims to be an open source alternative to commercial voice assistants (Alexa, Google Home, Siri).

Key characteristics of the project:
- Privacy-first design (100% local processing)
- Dual wake words (Jarvis for commands, Athena for knowledge)
- RAG-based knowledge retrieval
- Home Assistant integration
- Multi-zone voice coverage
- Guest mode for Airbnb/rental properties
- Admin interface for configuration

Without a commitment to open source principles, the project risks:
- Becoming too tightly coupled to specific infrastructure
- Including proprietary code or dependencies
- Poor documentation for external contributors
- Hardcoded credentials and secrets
- Difficult setup for new users
- Limited community adoption

## Decision

**Project Athena will be developed with open source release as a primary target from the beginning.**

This means all development decisions must consider:
1. **Code quality**: Production-ready, well-documented, testable
2. **Licensing**: Clear, permissive open source license (MIT or Apache 2.0)
3. **Documentation**: Self-explanatory code, comprehensive setup guides
4. **Security**: No hardcoded secrets, secure defaults
5. **Portability**: Works on common platforms (Mac, Linux, Docker, Kubernetes)
6. **Contribution-friendly**: Clear guidelines, welcoming to new contributors

## Consequences

### Positive

- **Community growth**: Open source attracts contributors, testers, and users
- **Better code quality**: Public scrutiny encourages best practices
- **Faster innovation**: Community contributions accelerate development
- **Transparency**: Users can audit privacy and security claims
- **Flexibility**: Users can customize and extend for their needs
- **Longevity**: Project survives beyond original developers
- **Reputation**: Demonstrates technical credibility and commitment to privacy

### Negative

- **Additional work**: Must write more documentation and examples
- **Security scrutiny**: Vulnerabilities will be publicly visible
- **Support burden**: Community expects help and issue resolution
- **Feature parity**: Can't use proprietary APIs or services without alternatives
- **Slower development**: Must consider broader use cases, not just personal setup

### Neutral

- Commercial use allowed (with attribution)
- Forks and derivatives encouraged
- No warranty or liability (standard open source)

## Implementation Principles

### 1. Code Quality Standards

**All code must be:**
- **Readable**: Clear variable names, logical structure, meaningful comments
- **Documented**: Docstrings for all public functions and classes
- **Tested**: Unit tests for core functionality, integration tests for workflows
- **Type-hinted**: Python type hints for better IDE support and safety
- **Linted**: Pass standard linters (black, flake8, mypy for Python; prettier, eslint for JS)
- **Modular**: Clear separation of concerns, reusable components

**Example pattern:**
```python
async def get_weather_forecast(
    location: str,
    days: int = 5
) -> Dict[str, Any]:
    """
    Get weather forecast for a location.

    Args:
        location: City name (e.g., "Los Angeles, CA")
        days: Number of days to forecast (1-5, default 5)

    Returns:
        Dictionary containing forecast data with structure:
        {
            "location": {"name": str, "country": str},
            "forecast": [{"date": str, "temp": float, ...}]
        }

    Raises:
        ValueError: If location not found or days out of range
        HTTPException: If weather API is unavailable
    """
    # Implementation...
```

### 2. No Secrets in Code

**NEVER commit:**
- API keys or tokens
- Passwords or credentials
- Private keys or certificates
- Personal information (IPs, emails, names)
- Infrastructure-specific paths

**ALWAYS use:**
- Environment variables for secrets
- `.env.example` files showing required variables (with dummy values)
- Clear documentation of required API keys
- Secure defaults (localhost, standard ports)
- Configuration files in `.gitignore`

**Example `.env.example`:**
```bash
# OpenWeatherMap API Key (get free key at https://openweathermap.org/api)
OPENWEATHER_API_KEY=your_api_key_here

# Home Assistant
HA_URL=http://192.168.1.100:8123
HA_TOKEN=your_long_lived_access_token_here

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Mac Studio/mini IPs (customize for your network)
MAC_STUDIO_IP=192.168.1.167
MAC_MINI_IP=192.168.1.181
```

### 3. Comprehensive Documentation

**Every feature must have:**

1. **README.md** at repository root:
   - Project overview and goals
   - Quick start guide (5 minutes to first working feature)
   - Architecture diagram
   - Hardware requirements
   - Link to full documentation

2. **docs/** directory with:
   - **INSTALLATION.md**: Detailed setup instructions
   - **ARCHITECTURE.md**: System design and component overview
   - **CONFIGURATION.md**: All configuration options explained
   - **DEPLOYMENT.md**: Production deployment guide
   - **TROUBLESHOOTING.md**: Common issues and solutions
   - **API.md**: API endpoints and usage examples
   - **CONTRIBUTING.md**: How to contribute code

3. **Inline documentation**:
   - Module docstrings explaining purpose
   - Function/class docstrings with examples
   - Complex logic explained with comments
   - Why decisions were made, not just what code does

4. **Example configurations**:
   - `config/examples/` directory with working examples
   - Docker Compose files for common setups
   - Kubernetes manifests with sensible defaults

### 4. Permissive Licensing

**License:** MIT or Apache 2.0 (TBD - will decide before first public release)

**License file requirements:**
- `LICENSE` file at repository root
- License header in all source files
- Third-party license attribution in `LICENSES/` directory
- Clear copyright statement

**Example license header:**
```python
# Copyright 2025 Project Athena Contributors
#
# Licensed under the MIT License (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
# https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
```

### 5. Platform Independence

**Support multiple deployment targets:**

1. **Local development:**
   - Mac (M1/M2/M3/M4)
   - Linux (Ubuntu 22.04+, Debian 11+)
   - Windows (via WSL2)

2. **Production deployment:**
   - Docker Compose (single machine)
   - Kubernetes (multi-node cluster)
   - Bare metal (systemd services)

3. **Hardware flexibility:**
   - CPU-only mode (slower but works everywhere)
   - GPU acceleration (NVIDIA, Apple Silicon)
   - Edge devices (Jetson, Raspberry Pi 5)

**Avoid:**
- Hardcoded paths (`/Users/jaystuart/...`)
- Platform-specific commands without alternatives
- Assuming specific hardware (document requirements)
- Proprietary dependencies without open source alternatives

**Example configuration:**
```python
# Bad: Hardcoded path
MODEL_PATH = "/Users/jaystuart/models/whisper-tiny.en"

# Good: Configurable with sensible default
MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", "/opt/athena/models/whisper-tiny.en")

# Better: Platform-aware defaults
import platform
if platform.system() == "Darwin":  # macOS
    DEFAULT_MODEL_PATH = os.path.expanduser("~/Library/Application Support/Athena/models")
else:  # Linux
    DEFAULT_MODEL_PATH = "/opt/athena/models"

MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", DEFAULT_MODEL_PATH)
```

### 6. Contribution Guidelines

**File:** `CONTRIBUTING.md`

Must include:
- How to set up development environment
- Code style guidelines (link to linters/formatters)
- How to run tests
- How to submit pull requests
- Issue templates for bugs and features
- Code of conduct (welcoming, inclusive community)

**Development workflow:**
```bash
# Clone repository
git clone https://github.com/yourusername/project-athena.git
cd project-athena

# Set up development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linters
black src/ tests/
flake8 src/ tests/
mypy src/

# Run service locally
cd src/rag/weather
python main.py
```

### 7. Security Best Practices

**All code must:**
- Validate user input (no SQL injection, XSS, command injection)
- Use parameterized queries for databases
- Escape HTML output
- Rate limit API endpoints
- Use HTTPS for production (document how to set up)
- Follow OWASP top 10 guidelines
- Document security assumptions

**Security disclosure:**
- `SECURITY.md` file with responsible disclosure process
- Private email for security reports
- 90-day disclosure timeline

### 8. Dependency Management

**Only use:**
- Open source dependencies with permissive licenses (MIT, Apache 2.0, BSD)
- Well-maintained packages (active development, security updates)
- Minimal dependencies (avoid dependency hell)

**Document:**
- Why each dependency is needed
- Alternatives considered
- License of each dependency

**Example `requirements.txt` with comments:**
```txt
# Web framework
fastapi>=0.104.0  # MIT License - Fast async API framework
uvicorn[standard]>=0.24.0  # BSD License - ASGI server

# HTTP client
httpx>=0.24.0  # BSD License - Async HTTP client for API calls

# Caching
redis>=5.0.0  # BSD License - Redis client with async support

# Logging
structlog>=23.2.0  # MIT License - Structured logging

# Environment variables
python-dotenv>=1.0.0  # BSD License - Load .env files
```

### 9. Example Configurations

**Provide working examples for:**
- Single-machine Docker Compose setup (most common)
- Kubernetes deployment (production)
- Bare metal installation (advanced users)
- Development setup (contributors)

**Example structure:**
```
examples/
├── docker-compose/
│   ├── single-machine/
│   │   ├── docker-compose.yml
│   │   ├── .env.example
│   │   └── README.md
│   └── distributed/
│       ├── docker-compose.yml
│       └── README.md
├── kubernetes/
│   ├── manifests/
│   ├── kustomization.yaml
│   └── README.md
└── bare-metal/
    ├── systemd/
    └── README.md
```

### 10. Testing Requirements

**All features must have:**

1. **Unit tests** (90%+ coverage):
   - Test individual functions
   - Mock external dependencies
   - Test edge cases and error handling

2. **Integration tests**:
   - Test component interactions
   - Test API endpoints
   - Test database operations

3. **End-to-end tests** (for critical paths):
   - Test complete workflows
   - Test with real dependencies (in CI)

**CI/CD pipeline:**
- Run tests on every PR
- Check code coverage
- Run linters/formatters
- Build Docker images
- Test on multiple platforms

## Specific Considerations for Phase 2

### Guest Mode (Open Source Considerations)

**Challenge:** Guest mode includes Airbnb calendar integration
**Solution:**
- Support multiple calendar sources (iCal standard, PMS webhooks)
- Document how to integrate with various vacation rental platforms
- Provide generic calendar API interface
- Example configurations for Airbnb, Vrbo, Guesty, Hostaway

**Privacy concerns:**
- Clear documentation of data retention policies
- Easy-to-understand PII scrubbing
- Opt-in features, not opt-out
- Guest data auto-purge on checkout

### RAG Services (Open Source Considerations)

**Challenge:** Some APIs require paid keys
**Solution:**
- Always provide free tier alternatives
- Document free vs paid API differences
- Provide fallback behavior when APIs unavailable
- Support multiple API providers per service type

**Examples:**
- Weather: OpenWeatherMap (free tier) + WeatherAPI + NOAA
- News: NewsAPI (free tier) + RSS feeds + Reddit
- Events: Eventbrite API + Ticketmaster + local RSS
- Stocks: Alpha Vantage (free) + Yahoo Finance + IEX Cloud

### Admin Interface (Open Source Considerations)

**Challenge:** Authentication complexity
**Solution:**
- Support multiple auth providers (Authentik, Keycloak, Auth0, basic auth)
- Document OAuth2/OIDC setup for each provider
- Provide development mode with mock authentication
- Clear security warnings for production deployment

## Repository Structure for Open Source

```
project-athena/
├── LICENSE                    # MIT or Apache 2.0
├── README.md                  # Project overview and quick start
├── CONTRIBUTING.md            # Contribution guidelines
├── SECURITY.md                # Security disclosure policy
├── CODE_OF_CONDUCT.md         # Community guidelines
├── .github/                   # GitHub-specific files
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/             # CI/CD pipelines
├── docs/                      # Comprehensive documentation
│   ├── INSTALLATION.md
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   ├── DEPLOYMENT.md
│   ├── TROUBLESHOOTING.md
│   └── API.md
├── examples/                  # Working example configurations
│   ├── docker-compose/
│   ├── kubernetes/
│   └── bare-metal/
├── src/                       # Source code
│   ├── gateway/
│   ├── orchestrator/
│   ├── rag/
│   ├── shared/
│   └── admin/
├── tests/                     # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── config/                    # Configuration examples
│   └── examples/
├── scripts/                   # Helper scripts
│   ├── install.sh
│   ├── test.sh
│   └── deploy.sh
├── deployment/                # Deployment configurations
│   ├── docker/
│   ├── kubernetes/
│   └── systemd/
└── LICENSES/                  # Third-party licenses
```

## Pre-Release Checklist

Before making the repository public:

**Legal:**
- [ ] Choose license (MIT or Apache 2.0)
- [ ] Add LICENSE file
- [ ] Review all dependencies for license compatibility
- [ ] Audit code for proprietary references
- [ ] Add license headers to all source files

**Security:**
- [ ] Remove all hardcoded secrets (audit with git-secrets)
- [ ] Review code for security vulnerabilities
- [ ] Set up security disclosure process
- [ ] Document security assumptions
- [ ] Add SECURITY.md

**Documentation:**
- [ ] Write comprehensive README.md
- [ ] Complete all docs/ files
- [ ] Add CONTRIBUTING.md
- [ ] Add CODE_OF_CONDUCT.md
- [ ] Create installation guides for all platforms
- [ ] Document all configuration options
- [ ] Add API documentation
- [ ] Create example configurations

**Code Quality:**
- [ ] 90%+ test coverage
- [ ] All tests passing
- [ ] Linters/formatters configured
- [ ] CI/CD pipeline working
- [ ] No hardcoded paths
- [ ] Platform-independent code

**Community:**
- [ ] Set up issue templates
- [ ] Set up PR template
- [ ] Create Discord/Slack community (optional)
- [ ] Set up GitHub Discussions
- [ ] Plan initial blog post/announcement

## Open Source Release Timeline

**Phase 1 (Private Development):**
- Current state: Building core features
- Goal: Get basic voice assistant working
- Timeline: 4-6 weeks

**Phase 2 (Preparation for Release):**
- Add guest mode, RAG services, quality tracking
- Write comprehensive documentation
- Clean up code, add tests
- Timeline: 6-8 weeks

**Phase 3 (Beta Release):**
- Limited public release to small community
- Gather feedback, fix bugs
- Improve documentation based on user feedback
- Timeline: 4-6 weeks

**Phase 4 (Public Release v1.0):**
- Full open source release
- Announce on HN, Reddit, Twitter
- Active community support
- Timeline: After Phase 3 complete

## Impact on Current Development

**Every feature in Phase 2 must:**

1. **Be documented** as if explaining to external contributors
2. **Have no secrets** in code (use .env.example)
3. **Support multiple platforms** (Mac, Linux, Docker)
4. **Include tests** (unit + integration)
5. **Follow code standards** (linting, type hints, docstrings)
6. **Have example configs** (working examples in `examples/`)
7. **Be privacy-respecting** (no telemetry without opt-in)
8. **Use open source dependencies** (check licenses)

**Code review questions to ask:**
- Can someone else deploy this without asking me questions?
- Are there any hardcoded secrets or personal info?
- Does this work on platforms other than my Mac?
- Is this code well-documented for external contributors?
- Would I feel comfortable showing this code publicly?

## References

**Similar open source voice assistant projects:**
- Rhasspy: https://github.com/rhasspy
- Home Assistant Voice: https://www.home-assistant.io/voice_control/
- Mycroft AI: https://github.com/MycroftAI
- Leon AI: https://github.com/leon-ai/leon

**Open source best practices:**
- GitHub Open Source Guide: https://opensource.guide/
- Semantic Versioning: https://semver.org/
- Keep a Changelog: https://keepachangelog.com/
- Contributor Covenant: https://www.contributor-covenant.org/

**License resources:**
- Choose a License: https://choosealicense.com/
- SPDX License List: https://spdx.org/licenses/

## Review and Updates

This decision should be reviewed:
- Before each major release
- When adding new dependencies
- When considering proprietary features
- When community feedback suggests changes

**Last Updated:** 2025-01-13
**Next Review:** Before Phase 2 completion
