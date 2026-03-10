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