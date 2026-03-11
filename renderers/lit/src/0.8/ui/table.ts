/*
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

import { html, css, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { Root } from "./root.js";
import { classMap } from "lit/directives/class-map.js";
import { styleMap } from "lit/directives/style-map.js";
import { structuralStyles } from "./styles.js";

@customElement("a2ui-table")
export class Table extends Root {
  @property({ type: Array })
  accessor headers: string[] = [];

  @property({ type: Array })
  accessor rows: string[][] = [];

  static styles = [
    structuralStyles,
    css`
      * {
        box-sizing: border-box;
      }

      :host {
        display: block;
        flex: var(--weight);
        min-height: 0;
        overflow: auto;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Google Sans', 'Roboto', sans-serif;
      }

      th, td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #e0e0e0;
      }

      th {
        background-color: #f5f5f5;
        font-weight: 600;
        color: #333;
      }

      td {
        background-color: #fff;
        color: #666;
      }

      tr:hover td {
        background-color: #fafafa;
      }
    `,
  ];

  render() {
    return html`<table
      class=${classMap(this.theme.components.Table || {})}
      style=${this.theme.additionalStyles?.Table
        ? styleMap(this.theme.additionalStyles?.Table)
        : nothing}
    >
      ${this.headers.length > 0 ? html`
        <thead>
          <tr>
            ${this.headers.map(
              (header) => html`<th>${header}</th>`
            )}
          </tr>
        </thead>
      ` : nothing}
      ${this.rows.length > 0 ? html`
        <tbody>
          ${this.rows.map(
            (row) => html`<tr>
              ${row.map((cell) => html`<td>${cell}</td>`)}
            </tr>`
          )}
        </tbody>
      ` : nothing}
    </table>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "a2ui-table": Table;
  }
}
