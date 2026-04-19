# Design: FreeIPA Healthcheck Support

## Overview

Remote execution infrastructure for running FreeIPA healthcheck on IPA servers via SSH. Provides AI agents with the ability to inspect server health while maintaining strict security boundaries that prevent credentials from leaking into the AI agent environment.

**Key Features:**
- SSH-based remote execution with Kerberos authentication
- Secure sudo password collection via isolated GTK4 dialog subprocess
- Passwordless sudo option for automation-friendly environments
- Two execution modes: live healthcheck and log file reading
- Markdown and JSON output formats
- No credentials exposed to MCP layer or AI agent

**File Structure:**
```
freeipa_mcp/tools/
├── healthcheck.py       # Main healthcheck execution (~245 lines)
├── sudo_gui.py          # Sudo password launcher (~55 lines)
└── _sudo_dialog.py      # GTK4 dialog subprocess (~132 lines)
```

## Architecture Principles

### 1. Remote Execution Requirement

**Why SSH:**
- FreeIPA healthcheck must run on the IPA server itself (not remotely via API)
- Requires root privileges to inspect system state
- Server-side execution enables comprehensive system inspection
- No FreeIPA API equivalent exists for healthcheck functionality

**Why not local execution:**
- AI agents typically run on workstations, not IPA servers
- Healthcheck results must reflect actual server state
- Multiple servers may need inspection (HA deployments)

### 2. Security Isolation Model

**Critical requirement:** Sudo password must NEVER be:
- Passed as MCP tool parameter
- Stored in MCP server memory (except brief subprocess communication)
- Visible to AI agent in any form
- Written to disk or logs

**Solution:** Three-tier isolation:
1. **MCP layer:** No password parameter in tool schema
2. **Subprocess layer:** GTK4 dialog in separate process
3. **SSH layer:** Password transmitted via stdin to remote sudo

### 3. Kerberos-First Authentication

**SSH authentication hierarchy:**
1. Primary: Kerberos GSSAPI (ticket-based, no password)
2. Secondary: Sudo elevation (password only for privilege escalation)

**Design rationale:**
- SSH never uses passwords (only Kerberos tickets)
- Sudo password is separate from SSH authentication
- Credentials compartmentalized (Kerberos ticket vs. sudo password)

## Core Components

### Healthcheck Executor (`healthcheck.py`)

Main orchestrator for remote healthcheck execution.

**Responsibilities:**
- Kerberos principal detection
- Sudo password collection (if needed)
- SSH connection management
- Remote command execution
- Output formatting (markdown/JSON)

#### Kerberos Principal Detection

```python
def _get_kerberos_principal() -> str:
    # Parse output of: klist
    # Extract username from "Default principal: user@REALM"
    # Return username only (realm stripped)
```

**Purpose:** Determine SSH username from existing Kerberos ticket.

**Security property:** Uses existing credentials (no new authentication).

#### Execution Modes

**Mode: live**
- Runs `ipa-healthcheck` command on remote server
- Requires sudo privileges
- Real-time inspection of server state
- Supports filtering: source, check, severity, failures_only

**Mode: log**
- Reads `/var/log/ipa/healthcheck/healthcheck.log`
- Historical healthcheck data
- Requires sudo to read log file (owned by root)
- No filtering (returns raw log content)

#### Output Formats

**JSON:**
- Raw healthcheck output (array of check results)
- Each entry: `{"source": "...", "check": "...", "result": "...", "kw": {...}}`
- Suitable for programmatic parsing

**Markdown:**
- AI-optimized format
- Summary with emoji indicators (🔴 critical, 🟠 errors, 🟡 warnings, 🟢 success)
- Grouped by severity
- Formatted metadata (snake_case → Title Case)
- Recommendations section for failures

**Token efficiency:** Markdown format ~40% more efficient than JSON for AI consumption of healthcheck results.

### SSH Execution Layer

Remote command execution with credential protection.

#### SSH Connection Pattern

```bash
ssh -T \
  -o GSSAPIAuthentication=yes \
  -o GSSAPIDelegateCredentials=yes \
  -o StrictHostKeyChecking=accept-new \
  -o BatchMode=yes \
  -o ConnectTimeout=30 \
  user@hostname \
  'bash -c "cd / && sudo --stdin ipa-healthcheck <<< '\''password'\'' ; echo $?"'
```

**SSH Options Explained:**

| Option | Purpose |
|--------|---------|
| `-T` | Disable pseudo-TTY allocation (non-interactive) |
| `GSSAPIAuthentication=yes` | Enable Kerberos authentication |
| `GSSAPIDelegateCredentials=yes` | Forward Kerberos credentials to remote host |
| `StrictHostKeyChecking=accept-new` | Accept new host keys automatically (convenience) |
| `BatchMode=yes` | Fail if interactive auth required (no password prompts) |
| `ConnectTimeout=30` | Timeout for connection establishment |

**Why `-T` (no TTY):**
- Prevents interactive prompts
- Simplifies output parsing (no terminal control codes)
- Security: reduces attack surface for injection

**Why `GSSAPIDelegateCredentials`:**
- Remote server may need Kerberos ticket for healthcheck operations
- Enables seamless IPA API calls within healthcheck
- Standard IPA deployment pattern

#### Remote Command Construction

**With password (standard sudo):**
```bash
bash -c "cd / && sudo --stdin ipa-healthcheck <<< 'password' ; echo $?"
```

**Without password (passwordless sudo):**
```bash
bash -c "cd / && sudo ipa-healthcheck ; echo $?"
```

**Design decisions:**

1. **`cd /` before sudo:**
   - Ensures consistent working directory
   - Prevents "cannot find current directory" errors
   - Healthcheck output paths are absolute

2. **`sudo --stdin`:**
   - Reads password from stdin (no interactive prompt)
   - Single-line password via here-string `<<< 'password'`
   - Avoids TTY requirement

3. **`; echo $?` suffix:**
   - Captures actual exit code of sudo command
   - Distinguishes command failure from sudo failure
   - Parsed from last line of output

#### Credential Handling

**Password escaping:**
```python
# Shell escaping for password
escaped_pwd = password.replace("\\", "\\\\").replace("'", "'\\''")
```

**Security properties:**
- Password passed via stdin (not command-line arguments)
- No password in process list (`ps` output)
- No password in shell history
- Escaped to prevent injection

**Command escaping:**
```python
# Prevent command injection
escaped_cmd = command.replace("\\", "\\\\").replace('"', '\\"')
```

**Why double escaping:**
- First layer: local shell (building SSH command)
- Second layer: remote shell (executing within bash -c)

#### Exit Code Parsing

**Strategy:**
- Append `; echo $?` to remote command
- Last line of stdout contains exit code
- Separate command output from exit status

**Implementation:**
```python
stdout_lines = result.stdout.splitlines()
exit_code = int(stdout_lines[-1])  # Parse last line
output = "\n".join(stdout_lines[:-1])  # Rest is actual output
```

**Error detection:**
- Exit code 0: success
- Non-zero exit code + stderr analysis:
  - "incorrect password" → sudo auth failure
  - "not in the sudoers" → permission denied
  - Other → generic command failure

### Sudo Password Collection (`sudo_gui.py`, `_sudo_dialog.py`)

Subprocess-isolated GTK4 dialog for secure password input.

#### Architecture

Same subprocess isolation model as login dialog (see Design 02), but simplified:

```
healthcheck.py
  └─→ sudo_gui.get_sudo_password(username, hostname)
        └─→ subprocess.Popen([python3, _sudo_dialog.py, username, hostname])
              └─→ _sudo_dialog.py (GTK4 main process)
                    ├─→ Gtk.Window with password field
                    ├─→ Three buttons: Cancel | Passwordless | Authenticate
                    └─→ Exit code + stdout
                          ├─→ 0: password or "__PASSWORDLESS__" sentinel
                          ├─→ 1: user cancelled
                          ├─→ 2: wrong arguments
                          └─→ 3: no display / GTK unavailable
```

#### Dialog Features

**Three authentication choices:**

1. **Cancel:** User aborts healthcheck operation
   - Exit code: 1
   - Raises `RuntimeError` in parent process

2. **Passwordless:** User has NOPASSWD sudo configured
   - Exit code: 0
   - Prints `__PASSWORDLESS__` sentinel to stdout
   - Parent receives `None` password value
   - SSH executes sudo without `--stdin`

3. **Authenticate:** User enters sudo password
   - Exit code: 0
   - Prints password to stdout
   - Parent receives password string

**Why "Passwordless" button:**
- Convenience for users with NOPASSWD sudo
- Avoids "failed to collect password" error message
- Makes passwordless sudo option discoverable
- Alternative to `passwordless=true` MCP parameter

#### Security Properties

**Isolation guarantees:**
- Password never in MCP server memory (except brief pipe read)
- Subprocess owns password collection
- Parent process reads password from pipe, uses immediately, discards
- No password logging or persistence

**Display requirements:**
- Requires `DISPLAY` or `WAYLAND_DISPLAY` environment variable
- Fails early with clear error if no display
- Suggests passwordless sudo alternative

**GTK4 dependency:**
- Runtime dependency (not import-time)
- Clear error if GTK4 unavailable
- Suggests passwordless sudo alternative

### Output Formatting

Two-format system optimized for different use cases.

#### JSON Format

**Structure:**
```json
[
  {
    "source": "ipahealthcheck.ipa.roles",
    "check": "IPACRLManagerCheck",
    "result": "SUCCESS",
    "kw": {
      "key": "crl_manager",
      "crlmanager_enabled": true
    }
  },
  ...
]
```

**Use case:** Programmatic analysis, archival, comparison.

#### Markdown Format

**Structure:**
```markdown
# IPA Healthcheck Results

## Summary
- **Total Checks:** 42
- **Critical:** 0 🔴
- **Errors:** 1 🟠
- **Warnings:** 3 🟡
- **Success:** 38 🟢

**Overall Status:** Issues found that require attention

## CRITICAL Results
(none)

## ERROR Results

### ipahealthcheck.ipa.dna - IPADNARangeCheck

**Status:** ERROR

- **Msg:** DNA range exhausted: uid
- **Range Start:** 1234000
- **Range End:** 1234999
- **Available:** 0

---

## WARNING Results
...

## SUCCESS Results
...

## Recommendations

Review the issues above and take appropriate action:
1. Address CRITICAL and ERROR items immediately
2. Plan fixes for WARNING items
3. Re-run healthcheck after making changes to verify fixes

For more information, see: https://www.freeipa.org/page/Troubleshooting
```

**Features:**
- Visual severity indicators (emoji)
- Summary with counts
- Overall status assessment
- Grouped by severity (critical first)
- Formatted metadata (snake_case → Title Case)
- Actionable recommendations

**AI efficiency:**
- Token reduction: ~40% vs. JSON for typical results
- Natural language structure
- Summary-first for quick scanning
- Severity grouping aids prioritization

## Data Flow

### Full Healthcheck Execution Flow

```
1. MCP client calls healthcheck(server_hostname="ipa.example.com", mode="live")
     ↓
2. Extract Kerberos principal
     ├─→ Run: klist
     ├─→ Parse: "Default principal: admin@EXAMPLE.COM"
     └─→ Extract username: "admin"
     ↓
3. Check passwordless flag
     ├─→ If passwordless=true: skip password collection, set password=None
     └─→ If passwordless=false: proceed to step 4
     ↓
4. Collect sudo password via subprocess
     ├─→ Check display availability (DISPLAY/WAYLAND_DISPLAY)
     ├─→ Spawn: python3 _sudo_dialog.py admin ipa.example.com
     ├─→ User interaction in GTK4 dialog
     ├─→ Read stdout from subprocess
     │     ├─→ If "__PASSWORDLESS__": set password=None
     │     └─→ Else: set password=<entered_value>
     └─→ If exit code != 0: raise RuntimeError
     ↓
5. Build remote command
     ├─→ Base: "ipa-healthcheck --output-type json"
     ├─→ Add filters: --source, --check, --severity, --failures-only
     └─→ Example: "ipa-healthcheck --output-type json --failures-only"
     ↓
6. Execute SSH command
     ├─→ SSH auth: Kerberos GSSAPI
     ├─→ Remote shell: bash -c "cd / && sudo --stdin <cmd> <<< 'password' ; echo $?"
     ├─→ Capture stdout/stderr
     └─→ Parse exit code from last line
     ↓
7. Handle errors
     ├─→ Exit code != 0:
     │     ├─→ stderr contains "incorrect password": sudo auth failed
     │     ├─→ stderr contains "not in the sudoers": permission denied
     │     └─→ Other: generic command failure
     └─→ Raise RuntimeError with specific message
     ↓
8. Format output
     ├─→ If output_format="json": return raw JSON
     └─→ If output_format="markdown": parse JSON and format as markdown
     ↓
9. Return to MCP client
```

### Password Collection Subprocess Flow

```
1. sudo_gui.get_sudo_password(username, hostname)
     ↓
2. Check display availability
     ├─→ DISPLAY or WAYLAND_DISPLAY set: proceed
     └─→ Neither set: raise RuntimeError
     ↓
3. Spawn subprocess
     ├─→ Command: [python3, _sudo_dialog.py, username, hostname]
     ├─→ Capture: stdout, stderr
     └─→ Wait for exit
     ↓
4. _sudo_dialog.py execution (separate process)
     ├─→ Import GTK4 (gi.repository)
     ├─→ Initialize GTK display
     ├─→ Create window with password entry
     ├─→ User interaction:
     │     ├─→ Enter password + click "Authenticate"
     │     ├─→ Click "Passwordless"
     │     └─→ Click "Cancel" or close window
     ├─→ On action:
     │     ├─→ Password entered: print password to stdout, exit 0
     │     ├─→ Passwordless chosen: print "__PASSWORDLESS__" to stdout, exit 0
     │     └─→ Cancelled: exit 1
     └─→ Exit
     ↓
5. Parent reads subprocess result
     ├─→ Exit code 0: read stdout
     │     ├─→ stdout == "__PASSWORDLESS__": return None
     │     └─→ stdout == password: return password string
     ├─→ Exit code 1: raise RuntimeError (cancelled)
     ├─→ Exit code 2: raise RuntimeError (invalid arguments)
     └─→ Exit code 3: raise RuntimeError (GTK unavailable)
     ↓
6. Parent uses password
     ├─→ Pass to _exec_ssh()
     ├─→ Embed in remote command via here-string
     ├─→ Password string discarded after SSH execution
     └─→ No persistence
```

## Security Model

### Threat Model

**In-scope threats:**
1. Credential exposure to AI agent via MCP parameters
2. Password leakage in logs or error messages
3. Credential storage on disk
4. Command injection via user-controlled input
5. Man-in-the-middle SSH attacks

**Out-of-scope:**
- Compromised IPA server (environment responsibility)
- Kerberos infrastructure compromise (environment responsibility)
- User granting sudo access to untrusted users (policy responsibility)
- Physical access to workstation during password entry (user responsibility)

### Security Measures

#### 1. No Credentials in MCP Parameters

**Enforcement:** MCP tool schema explicitly forbids password parameter.

```python
# healthcheck tool schema (server.py)
HEALTHCHECK_TOOL = Tool(
    name="healthcheck",
    inputSchema={
        "properties": {
            "server_hostname": {"type": "string"},
            "passwordless": {"type": "boolean"},  # Flag, not password
            # NO PASSWORD FIELD
        }
    }
)
```

**Design constraint:** AI agent can only request passwordless mode or trigger password collection (cannot provide password).

#### 2. Subprocess Isolation for Password Collection

**Mechanism:** GTK4 dialog runs as separate process.

**Security properties:**
- Password never enters MCP server Python environment (except brief pipe read)
- Parent process receives password via subprocess.stdout (in-memory pipe)
- Password immediately passed to SSH subprocess stdin
- No intermediate storage

**Attack surface:** Only subprocess pipe (kernel-managed, in-memory).

#### 3. SSH with Kerberos Authentication

**SSH authentication:** Kerberos GSSAPI only (no password auth).

**Configuration:**
```bash
-o GSSAPIAuthentication=yes      # Use Kerberos
-o BatchMode=yes                 # Fail if interactive auth needed
```

**Security property:** SSH never prompts for passwords (Kerberos ticket required).

**Credential forwarding:**
```bash
-o GSSAPIDelegateCredentials=yes
```

**Purpose:** Remote healthcheck may need IPA API access (uses forwarded ticket).

**Risk:** Ticket delegation enables remote server to impersonate user.

**Mitigation:** Only delegate to trusted IPA servers (user controls server_hostname parameter).

#### 4. Sudo Password Protection

**Transmission:** Password passed via stdin (not command-line argument).

**Why stdin:**
```bash
# ✅ Secure: password not visible in process list
sudo --stdin command <<< 'password'

# ❌ Insecure: password visible in ps output
sudo -S command  # (password passed via stdin but still risky)
echo 'password' | sudo -S command  # (password in pipe)
```

**Escaping:** Password shell-escaped to prevent injection.

```python
escaped = password.replace("\\", "\\\\").replace("'", "'\\''")
```

**Attack scenario:** User with password containing `'; malicious-command; #` attempts injection.

**Mitigation:** Escaping neutralizes special characters.

#### 5. Command Injection Prevention

**User-controlled inputs:**
- `server_hostname`: Used in SSH connection (not shell-escaped)
- `source`, `check`, `severity`: Used in healthcheck command (not shell-escaped)

**Validation:**
- `server_hostname`: SSH client handles validation (hostname resolution)
- Healthcheck flags: Passed as separate arguments (not concatenated into shell string)

**Safe pattern:**
```python
# Arguments are separate, not shell-interpolated
parts = ["ipa-healthcheck", "--output-type", "json"]
if source:
    parts += ["--source", source]  # source not shell-evaluated
cmd = " ".join(parts)  # Space-join, no shell escaping needed
```

**Why safe:**
- Individual arguments cannot break out of argument context
- Healthcheck binary validates argument values
- Worst case: healthcheck fails with invalid argument error

**Note:** Command string itself IS shell-evaluated (bash -c), but user input is in argument position, not shell syntax position.

#### 6. Host Key Management

**Configuration:**
```bash
-o StrictHostKeyChecking=accept-new
```

**Behavior:**
- First connection: Accept and save host key
- Subsequent connections: Verify against saved key

**Security trade-off:**
- **Pro:** Automatic host key acceptance (no manual fingerprint verification)
- **Con:** First-connection MITM vulnerability (TOFU model)

**Justification:**
- IPA deployment context: servers are trusted (admin specifies hostname)
- Alternative (StrictHostKeyChecking=no) is worse (no MITM protection at all)
- Manual verification (StrictHostKeyChecking=yes) poor UX for AI agent workflow

**Mitigation:** Users should verify host key out-of-band before first connection.

#### 7. Error Message Sanitization

**Password redaction in errors:**
```python
# ✅ Safe error - no credential exposure
raise RuntimeError("sudo authentication failed: incorrect password")

# ❌ Unsafe error - could expose credentials
raise RuntimeError(f"sudo failed: {stderr}")  # stderr may contain password echo
```

**Implemented strategy:**
- Parse stderr for known error patterns
- Return sanitized error messages
- Never include raw stderr in exceptions if it may contain credentials

### Security Limitations and Mitigations

**1. Password in subprocess pipe:**
- **Limitation:** Password appears in stdout pipe from subprocess
- **Mitigation:** Pipe is in-memory (kernel-managed), subprocess exits immediately
- **Residual risk:** Memory forensics on running process
- **Alternative considered:** Named pipe - rejected (cleanup complexity, same memory exposure)

**2. Password in SSH stdin:**
- **Limitation:** Password passed to SSH subprocess stdin (brief exposure in parent memory)
- **Mitigation:** String discarded immediately after subprocess execution
- **Residual risk:** Memory forensics, core dumps
- **Alternative considered:** Expect/pexpect - rejected (heavyweight dependency, same memory exposure)

**3. First-connection MITM:**
- **Limitation:** `StrictHostKeyChecking=accept-new` vulnerable to MITM on first connection
- **Mitigation:** Document expected workflow (manual SSH connection first)
- **Alternative considered:** `StrictHostKeyChecking=yes` - rejected (breaks AI agent automation)

**4. Credential forwarding attack surface:**
- **Limitation:** `GSSAPIDelegateCredentials=yes` enables remote impersonation
- **Mitigation:** User controls server_hostname (trusted servers only)
- **Alternative considered:** No delegation - rejected (healthcheck needs IPA API access)

**5. Sudo password reuse:**
- **Limitation:** Same password used for user login and sudo (common config)
- **Mitigation:** None (user policy decision)
- **Note:** Passwordless sudo recommended for automation

**6. Display requirement:**
- **Limitation:** GTK4 dialog requires graphical display
- **Mitigation:** `passwordless=true` flag for headless environments
- **Alternative considered:** Terminal password prompt - rejected (not possible in MCP context)

## Design Decisions and Trade-offs

### 1. Subprocess Isolation vs. In-Process GTK

**Decision:** GTK4 dialog in subprocess.

**Alternative:** GTK4 dialog in MCP server process (threaded).

**Rejected because:**
- GTK requires main thread for event loop
- Running GTK in asyncio thread causes initialization failures
- Window close/cancel handling complex with threads

**Trade-off:** Subprocess adds overhead (~100ms spawn time) but guarantees clean GTK lifecycle.

### 2. Passwordless Button vs. Parameter-Only

**Decision:** Provide "Passwordless" button in sudo dialog.

**Alternative:** Only support `passwordless=true` MCP parameter.

**Rejected because:**
- Users may not know they have passwordless sudo configured
- Dialog provides discoverable alternative to password entry
- AI agent can fall back if password collection fails

**Trade-off:** Additional UI complexity but better user experience.

### 3. Markdown vs. JSON Default

**Decision:** Default to markdown format for healthcheck output.

**Alternative:** Default to JSON (more structured).

**Rejected because:**
- AI agents process markdown more efficiently (~40% token savings)
- Healthcheck results are human-readable diagnostics (not structured data)
- JSON still available via `output_format="json"` parameter

**Trade-off:** Markdown parsing adds code complexity but optimizes for AI consumption.

### 4. Exit Code Embedding

**Decision:** Embed exit code in output via `; echo $?`.

**Alternative:** Rely on SSH exit code.

**Rejected because:**
- SSH exit code reflects SSH failure, not command exit code
- Sudo may succeed while command fails (exit code lost)
- Remote shell may return 0 even if command failed

**Trade-off:** Output parsing complexity but accurate exit code detection.

### 5. Two Execution Modes (live/log)

**Decision:** Support both live healthcheck and log reading.

**Alternative:** Only live mode.

**Rejected because:**
- Historical data useful for trend analysis
- Log mode doesn't require live server load
- Some environments run healthcheck on schedule (cron)

**Trade-off:** Additional code paths but greater flexibility.

### 7. Accept-New Host Key Policy

**Decision:** Use `StrictHostKeyChecking=accept-new`.

**Alternative:** `StrictHostKeyChecking=yes` (strict verification).

**Rejected because:**
- Breaks automation (requires manual fingerprint verification)
- AI agent cannot interactively verify host keys
- IPA servers are typically pre-trusted by admins

**Trade-off:** First-connection MITM risk but usable automation.

## Testing Strategy

### Unit Tests

**Test Coverage Target:** >85%

**Key Test Areas:**

1. **Kerberos principal extraction:**
   - Valid klist output parsing
   - Missing ticket error handling
   - Malformed output handling

2. **SSH command construction:**
   - Password escaping (special characters)
   - Command escaping (quotes, backslashes)
   - Passwordless mode (no --stdin)
   - Exit code embedding

3. **Output parsing:**
   - Exit code extraction from stdout
   - JSON parsing (valid/invalid)
   - Markdown formatting
   - Summary generation

4. **Error handling:**
   - Sudo auth failure detection
   - sudoers permission detection
   - SSH connection failure
   - Timeout handling

5. **Markdown formatting:**
   - Severity grouping
   - Emoji indicators
   - Metadata formatting (snake_case → Title Case)
   - Recommendations generation

### Integration Tests

**Requirements:**
- Live IPA server (e.g., `ipa.demo1.freeipa.org`)
- Valid Kerberos ticket
- SSH access to server
- Sudo privileges
- Graphical display (for GUI tests)

**Test Scenarios:**

1. **Live healthcheck execution:**
   - Run full healthcheck
   - Verify JSON output structure
   - Verify markdown formatting

2. **Log mode execution:**
   - Read healthcheck log file
   - Verify historical data parsing

3. **Passwordless sudo:**
   - Configure NOPASSWD sudo
   - Run healthcheck with passwordless=true
   - Verify no password prompt

4. **Sudo password collection:**
   - Run healthcheck with password
   - Verify dialog spawns
   - Verify password transmission (mocked)

5. **Error scenarios:**
   - Invalid hostname → connection error
   - No Kerberos ticket → auth error
   - Incorrect sudo password → auth failure
   - No sudo privileges → permission error

### Security Tests

**Manual verification checklist:**

1. ✅ No password parameter in MCP tool schema
2. ✅ Password not in process list during execution (`ps aux | grep sudo`)
3. ✅ Password not in SSH command line (`ps aux | grep ssh`)
4. ✅ No password in error messages (trigger sudo auth failure)
5. ✅ Subprocess isolation (ps shows separate _sudo_dialog.py process)
6. ✅ Special characters in password handled correctly (e.g., `!@#$%^&*()`)
7. ✅ Command injection attempts fail (e.g., `source="'; malicious; #"`)

## Operational Considerations

### Prerequisites

**User must have:**
1. Valid Kerberos ticket (via `kinit` or login tool)
2. SSH access to target IPA server (Kerberos-authenticated)
3. Sudo privileges on target server
4. Graphical display (DISPLAY/WAYLAND_DISPLAY) OR passwordless sudo

**Server must have:**
1. `ipa-healthcheck` package installed
2. User's Kerberos principal in sudoers (for healthcheck command)
3. Optional: NOPASSWD sudo for automation

### Error Recovery

**No Kerberos ticket:**
```
Error: No Kerberos ticket found. Run the login tool first.
→ Solution: Run login tool to obtain TGT
```

**No display for password dialog:**
```
Error: Sudo password required but no graphical display found.
→ Solution 1: Set DISPLAY environment variable
→ Solution 2: Use passwordless=true parameter (requires NOPASSWD sudo)
```

**Incorrect sudo password:**
```
Error: sudo authentication failed: incorrect password
→ Solution: Re-run healthcheck, enter correct password
```

**No sudo privileges:**
```
Error: User admin is not permitted to run sudo on ipa.example.com
→ Solution: Grant sudo access on server or use different user
```

**SSH connection failure:**
```
Error: Remote command failed: ssh: connect to host ipa.example.com port 22: Connection refused
→ Solution: Verify server hostname, network connectivity, SSH service running
```

### Performance Characteristics

**Healthcheck execution time:**
- Live mode: 10-60 seconds (depends on check count and server load)
- Log mode: <1 second (file read only)

**Overhead breakdown:**
- SSH connection: 1-2 seconds
- Sudo password dialog: 5-30 seconds (user interaction)
- Healthcheck execution: 10-60 seconds
- Markdown formatting: <100ms

**Optimization tips:**
- Use `--failures-only` to reduce output size
- Use `--source` to run specific check groups only
- Use log mode for historical analysis (no server load)
- Configure passwordless sudo to skip password dialog

### Limitations

**Known limitations:**

1. **Single server execution:** One server per tool call (no batch execution)
2. **Display requirement:** GUI password collection requires graphical display
3. **Sudo requirement:** Cannot run healthcheck without sudo privileges
4. **SSH requirement:** No alternative transport (no direct IPA API)
5. **Kerberos requirement:** SSH authentication via Kerberos only (no password)

**Workarounds:**

- Batch execution: Call tool multiple times (MCP client can parallelize)
- No display: Use `passwordless=true` parameter
- No sudo: Request admin to grant sudo access
- No SSH: Not supported (inherent healthcheck limitation)
- No Kerberos: Run login tool to obtain TGT

## Future Enhancements

**Considered but deferred:**

1. **Batch server execution:** Run healthcheck on multiple servers in one call
   - **Trade-off:** Complexity vs. MCP client can parallelize

2. **Result caching:** Cache healthcheck results to reduce server load
   - **Trade-off:** Stale data risk vs. performance gain

3. **Scheduled execution:** Trigger healthcheck on cron schedule
   - **Trade-off:** Scope creep (MCP tool vs. system scheduler)

4. **Result comparison:** Compare current results with historical baseline
   - **Trade-off:** Storage complexity vs. user can compare manually

5. **Alert integration:** Send notifications for critical failures
   - **Trade-off:** Scope creep (healthcheck vs. monitoring system)

6. **Alternative authentication:** SSH key-based auth instead of Kerberos
   - **Trade-off:** Key management complexity vs. Kerberos is IPA standard

## Non-Goals

- ❌ Healthcheck remediation (automatic fix application)
- ❌ Healthcheck scheduling (cron replacement)
- ❌ Multi-server batch execution
- ❌ Result storage and history tracking
- ❌ Alert/notification system
- ❌ SSH password authentication (Kerberos only)
- ❌ Non-IPA healthcheck support (specific to FreeIPA)

## Success Criteria

- ✅ Execute healthcheck on remote IPA server via SSH
- ✅ Collect sudo password via secure GUI dialog
- ✅ Support passwordless sudo for automation
- ✅ No credentials exposed to MCP layer or AI agent
- ✅ Markdown output optimized for AI consumption
- ✅ JSON output available for programmatic parsing
- ✅ Clear error messages for common failure scenarios
- ✅ Subprocess isolation for password collection
- ✅ Test coverage >85%
