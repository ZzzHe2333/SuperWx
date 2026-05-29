# wxauto4 Manual Test Checklist

Before running online tests, verify:

## Environment
- [ ] Windows 10/11 with WeChat 4.x installed and logged in
- [ ] WeChat main window visible (not minimized)
- [ ] Python 3.8+ with `uiautomation` and `fastapi` installed

## Pre-flight
- [ ] `git status` shows clean working tree
- [ ] `git checkout -b test/manual-YYYY-MM-DD` on a test branch
- [ ] Backup any important WeChat data

## Test Steps

### 1. Doctor check
```bash
python -m wxauto4 doctor
```
- [ ] main_window: OK
- [ ] chat_message_page: OK
- [ ] session_list: OK
- [ ] chat_message_list: OK
- [ ] chat_input_field: OK
- [ ] send_button: OK (may need text in input first)

### 2. Probe all controls
```bash
python tests/probe_wechat_locator.py
```
- [ ] All 8 controls found

### 3. Message reading (dry_run)
```bash
python tests/manual_test_wechat.py --show-messages
```
- [ ] Messages displayed without error

### 4. Session list (dry_run)
```bash
python tests/manual_test_wechat.py --show-sessions
```
- [ ] Sessions listed

### 5. Send text (REAL - careful!)
```bash
python tests/manual_test_wechat.py --send --target "文件传输助手" --message "test from wxauto4"
```
- [ ] Message sent successfully
- [ ] No errors

### 6. Send file (REAL - careful!)
```bash
python tests/manual_test_wechat.py --send-file --target "文件传输助手" --file "path/to/test.txt"
```
- [ ] File sent successfully

### 7. History messages
```bash
python tests/test_history_message_module08.py --send --n 10
```
- [ ] Historical messages retrieved
- [ ] No duplicates

### 8. REST API
```bash
# Terminal 1:
python -m wxauto4.api.main
# Terminal 2:
curl http://127.0.0.1:8760/health
```
- [ ] Health check returns ok

### 9. MCP server
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python -m wxauto4_mcp.server
```
- [ ] Returns valid JSON-RPC response

### 10. Safety check
```bash
python tests/safety_check.py
```
- [ ] No dangerous patterns found

### 11. Regression (offline)
```bash
python tests/regression_all.py
```
- [ ] All offline tests pass

## Notes
- Always test on a non-critical chat first (e.g., "文件传输助手")
- Keep dry_run=True unless explicitly testing real sends
- Report issues with UI dump: `python -m wxauto4 doctor --dump-on-fail`
