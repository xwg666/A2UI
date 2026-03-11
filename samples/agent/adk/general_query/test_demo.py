CHANGE_PASSWORD_A2UI=[
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
                  "header-row",
                  "account-list",
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
                "literalString": "请在下面的列表中勾选您需要修改密码的账号，每次只能修改一个账号。"
              }
            }
          }
        },
        {
          "id": "header-row",
          "component": {
            "Row": {
              "children": {
                "explicitList": [
                  "header-check",
                  "header-ltcode",
                  "header-display",
                  "header-type"
                ]
              },
              "distribution": "spaceBetween",
              "alignment": "center"
            }
          }
        },
        {
          "id": "header-check",
          "component": {
            "Text": {
              "text": {
                "literalString": "   "
              }
            }
          }
        },
        {
          "id": "header-ltcode",
          "component": {
            "Text": {
              "text": {
                "literalString": "Ltcode"
              }
            }
          }
        },
        {
          "id": "header-display",
          "component": {
            "Text": {
              "text": {
                "literalString": "Display Name"
              }
            }
          }
        },
        {
          "id": "header-type",
          "component": {
            "Text": {
              "text": {
                "literalString": "账号类型"
              }
            }
          }
        },
        {
          "id": "account-list",
          "component": {
            "List": {
              "direction": "vertical",
              "children": {
                "template": {
                  "componentId": "account-card",
                  "dataBinding": "/items"
                }
              }
            }
          }
        },
        {
          "id": "account-card",
          "component": {
            "Card": {
              "child": "account-row"
            }
          }
        },
        {
          "id": "account-row",
          "component": {
            "Row": {
              "children": {
                "explicitList": [
                  "account-checkbox",
                  "account-ltcode",
                  "account-display",
                  "account-type"
                ]
              },
              "distribution": "spaceBetween",
              "alignment": "center"
            }
          }
        },
        {
          "id": "account-checkbox",
          "component": {
            "CheckBox": {
              "label": {
                "literalString": ""
              },
              "value": {
                "path": "/checked"
              }
            }
          }
        },
        {
          "id": "account-ltcode",
          "component": {
            "Text": {
              "text": {
                "path": "/ltcode"
              }
            }
          }
        },
        {
          "id": "account-display",
          "component": {
            "Text": {
              "text": {
                "path": "/displayName"
              }
            }
          }
        },
        {
          "id": "account-type",
          "component": {
            "Text": {
              "text": {
                "path": "/accountType"
              }
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
              "primary": True,
              "action": {
                "name": "confirm_password_change"
              }
            }
          }
        },
        {
          "id": "confirm-text",
          "component": {
            "Text": {
              "text": {
                "literalString": "确定"
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
          "key": "items",
          "valueMap": [
            {
              "key": "item1",
              "valueMap": [
                { "key": "ltcode", "valueString": "botland" },
                { "key": "displayName", "valueString": "botland" },
                { "key": "accountType", "valueString": "Function" },
                { "key": "checked", "valueBoolean": True }
              ]
            },
            {
              "key": "item2",
              "valueMap": [
                { "key": "ltcode", "valueString": "liangsj4" },
                { "key": "displayName", "valueString": "liangsj4" },
                { "key": "accountType", "valueString": "" },
                { "key": "checked", "valueBoolean": False }
              ]
            }
          ]
        }
      ]
    }
  }
]
meeting_result=[
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
                  "date-picker",
                  "time-picker",
                  "people-input",
                  "device-label",
                  "device-row",
                  "confirm-button"
                ]
              },
              "spacing": 16,
              "padding": 24
            }
          }
        },
        {
          "id": "title-text",
          "component": {
            "Text": {
              "text": { "literalString": "会议室预订" },
              "usageHint": "h4",
              "style": "font-weight: bold; text-align: center; margin-bottom: 24px;"
            }
          }
        },
        {
          "id": "date-picker",
          "component": {
            "DateTimeInput": {
              "label": { "literalString": "Date" },
              "value": { "literalString": "2024/01/15" },
              "enableDate": True,
              "enableTime": False,
              "format": "yyyy/MM/dd"
            }
          }
        },
        {
          "id": "time-picker",
          "component": {
            "DateTimeInput": {
              "label": { "literalString": "Time" },
              "value": { "literalString": "--:--" },
              "enableDate": False,
              "enableTime": True,
              "placeholder": "--:--"
            }
          }
        },
        {
          "id": "people-input",
          "component": {
            "TextField": {
              "label": { "literalString": "人数" },
              "text": { "literalString": "10" },
              "textFieldType": "number"
            }
          }
        },
        {
          "id": "device-label",
          "component": {
            "Text": {
              "text": { "literalString": "设备需求：" },
              "usageHint": "body",
              "style": "font-weight: bold; margin-top: 8px;"
            }
          }
        },
        {
          "id": "device-row",
          "component": {
            "Row": {
              "children": {
                "explicitList": ["check-projector", "check-whiteboard"]
              },
              "distribution": "start",
              "alignment": "center",
              "spacing": 24
            }
          }
        },
        {
          "id": "check-projector",
          "component": {
            "CheckBox": {
              "label": { "literalString": "投影仪" },
              "value": { "path": "/设备/投影仪" },
              "checked": True
            }
          }
        },
        {
          "id": "check-whiteboard",
          "component": {
            "CheckBox": {
              "label": { "literalString": "白板" },
              "value": { "path": "/设备/白板" },
              "checked": False
            }
          }
        },
        {
          "id": "confirm-button",
          "component": {
            "Button": {
              "child": "confirm-text",
              "action": {
                "name": "confirm_booking",
                "context": [
                  { "key": "date", "value": { "path": "/日期" } },
                  { "key": "time", "value": { "path": "/时间" } },
                  { "key": "people", "value": { "path": "/人数" } },
                  { "key": "projector", "value": { "path": "/设备/投影仪" } },
                  { "key": "whiteboard", "value": { "path": "/设备/白板" } }
                ]
              },
              "style": "background-color: #9F8BFF; color: white; border-radius: 24px; padding: 12px 32px; font-weight: bold;"
            }
          }
        },
        {
          "id": "confirm-text",
          "component": {
            "Text": {
              "text": { "literalString": "确认预订" },
              "style": "color: white;"
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
        { "key": "日期", "valueString": "2024/01/15" },
        { "key": "时间", "valueString": "" },
        { "key": "人数", "valueString": "10" },
        {
          "key": "设备",
          "valueMap": [
            { "key": "投影仪", "valueBoolean": True },
            { "key": "白板", "valueBoolean": False }
          ]
        }
      ]
    }
  }
]
table_result = [
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
                "explicitList": ["editor-table"]
              }
            }
          }
        },
        {
          "id": "editor-table",
          "component": {
            "Table": {
              "headers": ["编辑器", "价格", "中文支持"],
              "rows": [
                ["Trae", "免费", "中文支持好"],
                ["Cursor", "付费", "中文一般"],
                ["Copilot", "付费", "中文差"]
              ]
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
      "contents": []
    }
  }
]