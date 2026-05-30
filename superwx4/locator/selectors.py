"""UI selector fallback chains for WeChat 4.x controls.

Each key maps to a list of selector dicts tried in order.
The first match that Exists() wins.

Selector dict keys:
  - method:  UIA method name (e.g. "GroupControl", "ListControl")
  - All other keys are passed as kwargs to that method.
"""

SELECTORS = {
    "chat_message_page": [
        {"method": "GroupControl", "AutomationId": "chat_message_page", "ClassName": "mmui::ChatMessagePage"},
        {"method": "GroupControl", "AutomationId": "chat_message_page"},
        {"method": "GroupControl", "ClassName": "mmui::ChatMessagePage"},
    ],
    "message_view": [
        {"method": "GroupControl", "ClassName": "mmui::MessageView"},
    ],
    "chat_message_list": [
        {"method": "ListControl", "AutomationId": "chat_message_list", "ClassName": "mmui::RecyclerListView"},
        {"method": "ListControl", "AutomationId": "chat_message_list"},
        {"method": "ListControl", "ClassName": "mmui::RecyclerListView"},
    ],
    "chat_input_field": [
        {"method": "EditControl", "AutomationId": "chat_input_field", "ClassName": "mmui::ChatInputField"},
        {"method": "EditControl", "AutomationId": "chat_input_field"},
        {"method": "EditControl", "ClassName": "mmui::ChatInputField"},
    ],
    "send_button": [
        {"method": "ButtonControl", "Name": "发送", "ClassName": "mmui::XOutlineButton"},
        {"method": "ButtonControl", "Name": "发送"},
        {"method": "ButtonControl", "Name": "发送(S)"},
        {"method": "ButtonControl", "Name": "Send"},
    ],
    "input_view": [
        {"method": "GroupControl", "ClassName": "mmui::InputView"},
    ],
    "session_list": [
        {"method": "ListControl", "AutomationId": "session_list"},
        {"method": "ListControl", "ClassName": "mmui::XTableView"},
    ],
}
