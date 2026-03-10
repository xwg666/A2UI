result=[
  {
    "beginRendering": {
      "surfaceId": "default",
      "root": "root-column"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "default",
      "components": [
        {
          "id": "root-column",
          "component": {
            "Column": {
              "children": {
                "explicitList": [
                  "title-text",
                  "account-selector",
                  "button-row"
                ]
              }
            }
          }
        },
        {
          "id": "title-text",
          "component": {
            "Text": {
              "text": {
                "literalString": "请选择您需要修改密码的账号（单选）："
              }
            }
          }
        },
        {
          "id": "account-selector",
          "component": {
            "MultipleChoice": {
              "description": "选择一个账号",
              "selections": {
                "path": "/selectedAccount"
              },
              "options": [
                {
                  "label": {"literalString": "botland (Function)"},
                  "value": "botland"
                },
                {
                  "label": {"literalString": "liangsj4"},
                  "value": "liangsj4"
                }
              ],
              "variant": "checkbox"
            }
          }
        },
        {
          "id": "button-row",
          "component": {
            "Row": {
              "children": {
                "explicitList": [
                  "confirm-button"
                ]
              },
              "distribution": "start"
            }
          }
        },
        {
          "id": "confirm-button",
          "component": {
            "Button": {
              "child": "confirm-text",
              "action": {
                "name": "confirm_password_change",
                "context": [
                  {"key": "selectedAccount", "value": {"path": "/selectedAccount"}}
                ]
              }
            }
          }
        },
        {
          "id": "confirm-text",
          "component": {
            "Text": {
              "text": {
                "literalString": "确定修改密码"
              }
            }
          }
        }
      ]
    }
  },
  {
    "dataModelUpdate": {
      "surfaceId": "default",
      "path": "/",
      "contents": [
        {
          "key": "selectedAccount",
          "valueString": ""
        }
      ]
    }
  }
]
