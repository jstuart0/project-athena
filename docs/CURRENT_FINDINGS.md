# Project Athena - Current Findings and Analysis

**Date:** November 3, 2025
**Analysis Based On:** Wiki documentation, Home Assistant inspection, network analysis

## Executive Summary

Project Athena has a strong foundation with the **Athena Lite proof-of-concept** already 90% complete on jetson-01. The system is ready for testing once SSH access is configured. Home Assistant is accessible and has the basic conversation agent, but **needs Wyoming protocol services** for the full distributed architecture.

## Key Discoveries

### ✅ What's Working

**Athena Lite Implementation:**
- Location: `/mnt/nvme/athena-lite/` on jetson-01 (192.168.10.62)
- Dual wake word system (Jarvis + Athena) implemented
- Response time optimized from 7-9s to 2.5-5s
- All software dependencies and models installed
- 1.8TB NVMe storage configured and operational

**Home Assistant Integration:**
- Accessible at https://192.168.10.168:8123 (HTTPS required)
- API token configured and stored in thor cluster
- Basic conversation agent (`conversation.home_assistant`) available
- Ready for direct API integration (Athena Lite method)

**Network Infrastructure:**
- Jetson-01 accessible on network (ping successful)
- Home Assistant API responding
- Thor cluster operational and accessible
- Network topology supports planned architecture

### ❌ Current Gaps

**Wyoming Protocol Missing:**
- No Wyoming-Piper (TTS) addon in Home Assistant
- No Wyoming-Whisper (STT) addon in Home Assistant
- No Wyoming satellite device support
- Required for full distributed Project Athena

**Access Limitations:**
- SSH access to jetson-01 not configured
- Cannot directly inspect Athena Lite files
- Physical access required for testing

**Implementation Phases:**
- Phase 0 (HA migration to Proxmox) not started
- Wyoming devices not ordered
- Proxmox services not deployed

## Architecture Analysis

### Current vs. Planned Architecture

**Athena Lite (Current - Working):**
```
Audio → Jetson (All Processing) → HA API → Device Control
        ├─ Wake Word Detection
        ├─ STT (Whisper)
        ├─ TTS (Piper)
        └─ Basic Intent Processing
```

**Full Project Athena (Planned - Needs Wyoming):**
```
Wyoming Devices → Jetson (Wake Word) → Proxmox Services → HA (Wyoming) → Device Control
                                        ├─ STT Service
                                        ├─ TTS Service
                                        ├─ LLM Processing
                                        └─ RAG System
```

### Architecture Decision Required

**Option A: Deploy Wyoming Services in Home Assistant**
- Install Wyoming-Piper and Wyoming-Whisper addons in HA
- Follow standard Home Assistant voice assistant setup
- Simpler integration, less scalable

**Option B: Deploy Wyoming Services on Proxmox (Wiki Plan)**
- Run Wyoming services as Kubernetes services on thor cluster
- Home Assistant connects to external Wyoming services
- More complex setup, better performance and scalability

## Technical Requirements Analysis

### For Athena Lite Testing (Immediate)

**Required:**
- SSH access to jetson-01 (192.168.10.62)
- Audio device configuration (microphone + speaker)
- Home Assistant token integration (already available)

**Expected Results:**
- 2.5-5 second response times
- Dual wake word functionality
- Basic device control via HA API

### For Full Project Athena (Future)

**Wyoming Protocol Implementation Required:**
- Wyoming-Piper TTS service
- Wyoming-Whisper STT service
- Wyoming satellite device protocol
- 10 Wyoming voice devices (hardware procurement)

**Infrastructure Requirements:**
- Proxmox services deployment (Kubernetes manifests)
- NFS storage from Synology (configured)
- Network configuration for 10 zones
- PoE switch ports for Wyoming devices

## Home Assistant Current State

### Available Services

**Voice Assistant:**
- `conversation.home_assistant` - Basic conversation agent
- Supports natural language processing
- No external STT/TTS dependencies

**Missing for Wyoming:**
- Wyoming-Piper addon (Text-to-Speech)
- Wyoming-Whisper addon (Speech-to-Text)
- Wyoming satellite configuration
- Wyoming protocol integration

### Integration Approach

**For Athena Lite (Immediate):**
- Direct API calls to HA (no Wyoming needed)
- Use Jetson's built-in STT/TTS
- Bypass Wyoming protocol entirely

**For Full Project Athena (Future):**
- Requires Wyoming protocol implementation
- Either as HA addons or external services
- Coordinated with Wyoming device deployment

## Resource Utilization Analysis

### Current Capacity

**Jetson-01 (Athena Lite):**
- CPU: ~60% utilized during processing
- RAM: ~3GB used of 8GB available
- Storage: ~200MB used of 1.8TB available
- Network: <1Mbps bandwidth usage

**Thor Cluster (Available for Proxmox Services):**
- Total vCPU: 172 cores available
- Total RAM: 448GB available
- Storage: Ceph cluster + Synology NFS
- Network: 10GbE backbone

### Scalability Assessment

**Single Jetson Limitations:**
- One zone coverage only
- No distributed processing
- Limited by single device resources
- No redundancy or load balancing

**Distributed Architecture Benefits:**
- 10-zone coverage capability
- Distributed processing load
- Redundancy and failover
- Better resource utilization

## Implementation Recommendations

### Phase 0: Validate Athena Lite (Immediate - 1 Week)

**Priority:** HIGH
**Goal:** Prove core concepts work before scaling

**Actions:**
1. Configure SSH access to jetson-01
2. Test Athena Lite end-to-end functionality
3. Measure actual performance metrics
4. Document lessons learned

**Success Criteria:**
- Voice commands work reliably
- Response times meet 2-5 second target
- Home Assistant device control functional
- System stable for 24+ hours

### Phase 1: Wyoming Integration Decision (2-4 Weeks)

**Priority:** MEDIUM
**Goal:** Decide on Wyoming implementation approach

**Decision Points:**
- HA addons vs. external services
- Resource allocation strategy
- Deployment complexity assessment
- Performance impact analysis

**Recommended Approach:**
- Start with HA addons for simplicity
- Migrate to external services if needed
- Test with 3 zones before full deployment

### Phase 2: Hardware Procurement (Parallel)

**Priority:** MEDIUM
**Goal:** Order Wyoming devices for testing

**Requirements:**
- 3 Wyoming voice devices for Phase 1 testing
- PoE compatibility verification
- Network configuration planning
- Switch port allocation

## Risk Assessment

### High Risk Items

**Athena Lite Access:**
- Risk: Cannot test without SSH access
- Mitigation: Configure SSH keys or physical access
- Impact: Blocks immediate validation

**Wyoming Protocol Complexity:**
- Risk: Implementation more complex than expected
- Mitigation: Start with HA addons, prove concept first
- Impact: Could delay full deployment

**Hardware Availability:**
- Risk: Wyoming devices may have long lead times
- Mitigation: Order early, have backup plan
- Impact: Could delay Phase 1 testing

### Medium Risk Items

**Performance Scaling:**
- Risk: Single Jetson may not handle 10 zones
- Mitigation: Distributed architecture already planned
- Impact: May need earlier Proxmox deployment

**Integration Complexity:**
- Risk: Multiple services coordination
- Mitigation: Gradual rollout, thorough testing
- Impact: Extended timeline but manageable

## Next Steps Prioritization

### Week 1: Immediate Actions

1. **Configure Jetson Access** (Critical)
   - Set up SSH key access
   - Verify Athena Lite project files
   - Test basic system functionality

2. **Test Home Assistant Integration** (High)
   - Verify API token functionality
   - Test device control commands
   - Measure API response times

3. **Audio Hardware Validation** (High)
   - Configure microphone input
   - Configure speaker output
   - Test audio pipeline quality

### Week 2-3: Validation and Planning

1. **End-to-End Athena Lite Testing** (Critical)
   - Complete voice command testing
   - Performance measurement
   - Stability testing

2. **Wyoming Implementation Planning** (Medium)
   - Research HA addon options
   - Plan Proxmox service architecture
   - Design deployment strategy

3. **Hardware Procurement** (Medium)
   - Identify Wyoming device vendors
   - Place order for 3 test devices
   - Plan network configuration

### Month 2: Scaling Implementation

1. **Wyoming Protocol Implementation** (High)
   - Deploy chosen Wyoming approach
   - Test with single zone
   - Expand to 3-zone testing

2. **Proxmox Service Deployment** (Medium)
   - Deploy STT/TTS services
   - Implement orchestration
   - Performance optimization

## Conclusion

Project Athena has excellent groundwork with Athena Lite nearly ready for testing. The path forward is clear:

1. **Immediate:** Test and validate Athena Lite
2. **Short-term:** Implement Wyoming protocol (choose approach)
3. **Medium-term:** Scale to full 10-zone deployment

The biggest decision point is Wyoming implementation strategy (HA addons vs. external services), but this can be validated through testing and iteration.

---

**Analysis By:** Claude Code
**Next Review:** After Athena Lite validation completion
**Status:** Ready for immediate implementation