---
name: Project Status - InterJob Operations 2026
description: Current active initiatives, blockers, and what's being worked on
type: project
---

**Active Initiatives** (as of 2026-05-03):

1. **Skills Library Sync** (✅ DONE)
   - Imported 628 Python skills from local AUTOMATE/ to CODE/SKILLS/
   - All skills discoverable by subagents
   
2. **Subagent Setup** (🔧 IN PROGRESS)
   - 14 specialist agents configured in .claude/agents/
   - Smart dispatch system documented but not yet wired (keyword → subagent routing)
   - Next: Test each agent, verify dispatch rules work

3. **Z.AI Integration** (⚠️ BLOCKED - SERVICE ISSUE)
   - Goose custom_z.ai.json provider config: ✅ NOW RESTORED
   - Environment variable CUSTOM_Z.AI_API_KEY: ✅ NOW SET
   - Z.AI API endpoints: ❌ BROKEN (404 errors on /api/anthropic)
   - **Status**: Ready to use when/if Z.AI fixes their service; not urgent

4. **PostgreSQL Access** (❌ NOT INSTALLED)
   - Need to install PostgreSQL 18 or tunnel to raspibig
   - Blocker for `pg-enricher` subagent (pipeline steps 1-46)
   - Decision pending: local install vs remote SSH tunnel

5. **Windows 11 Recovery** (🔧 IN PROGRESS)
   - Previous W11 installation configuration recovered from D:\MEMORY\DATA\OPENDATA/
   - Goose + OpenCode + Z.AI setup restored
   - SSH keys: ✅ READY, testing connection to raspibig

**Critical Blockers**:
- PostgreSQL not accessible (need to install or tunnel)
- SSH connection to raspibig: testing now

**Next Steps**:
1. Verify SSH works to raspibig
2. Decide on PostgreSQL (install vs tunnel)
3. Test all 5 subagents
4. Wire up smart dispatch system
5. Git cleanup (permission issues, pending deletes)
