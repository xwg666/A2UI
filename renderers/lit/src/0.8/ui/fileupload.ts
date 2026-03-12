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
import { customElement, property, state } from "lit/decorators.js";
import { Root } from "./root.js";
import { StateEvent } from "../events/events.js";
import { classMap } from "lit/directives/class-map.js";
import * as Types from "@a2ui/web_core/types/types";
import { styleMap } from "lit/directives/style-map.js";
import { structuralStyles } from "./styles.js";

@customElement("a2ui-fileupload")
export class FileUpload extends Root {
  @property({ type: Boolean })
  accessor multiple: boolean = false;

  @property({ type: String })
  accessor accept: string = "";

  @property({ type: Boolean })
  accessor directory: boolean = false;

  @property()
  accessor action: Types.Action | null = null;

  @state()
  private accessor _selectedFiles: File[] = [];

  @state()
  private accessor _uploadProgress: number = -1;

  static styles = [
    structuralStyles,
    css`
      :host {
        display: block;
        flex: var(--weight);
        min-height: 0;
      }

      .file-upload-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .file-input-wrapper {
        position: relative;
        display: inline-block;
      }

      .file-input-wrapper input[type="file"] {
        position: absolute;
        left: 0;
        top: 0;
        opacity: 0;
        width: 100%;
        height: 100%;
        cursor: pointer;
      }

      .upload-button {
        display: inline-block;
        padding: 8px 16px;
        background-color: #1976d2;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        text-align: center;
      }

      .upload-button:hover {
        background-color: #1565c0;
      }

      .file-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-top: 8px;
      }

      .file-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px;
        background-color: #f5f5f5;
        border-radius: 4px;
        font-size: 12px;
      }

      .file-name {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .remove-button {
        background: none;
        border: none;
        color: #f44336;
        cursor: pointer;
        font-size: 16px;
        padding: 0 4px;
      }

      .progress-bar {
        width: 100%;
        height: 4px;
        background-color: #e0e0e0;
        border-radius: 2px;
        margin-top: 8px;
        overflow: hidden;
      }

      .progress-fill {
        height: 100%;
        background-color: #1976d2;
        transition: width 0.3s ease;
      }
    `,
  ];

  #triggerClick() {
    const input = this.shadowRoot?.querySelector('input[type="file"]') as HTMLInputElement | null;
    if (input) {
      input.click();
    }
  }

  #handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this._selectedFiles = Array.from(input.files);
      // 将文件信息写入 data model
      this.#updateDataModel();
    }
  }

  #removeFile(index: number) {
    this._selectedFiles = this._selectedFiles.filter((_, i) => i !== index);
    this.#updateDataModel();
  }

  #updateDataModel() {
    if (!this.processor) {
      return;
    }

    // 构建文件信息数组
    const fileInfos = this._selectedFiles.map(file => ({
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified
    }));

    // 写入 data model
    // 使用 dataContextPath 作为路径，默认为 /files
    const surfaceId = this.surfaceId || "default";
    const path = this.dataContextPath || "/files";

    console.log("[FileUpload] Updating data model:", { path, fileInfos });

    // 直接通过 processor 更新数据
    (this.processor as any).setDataByPath(
      (this.processor as any).getOrCreateSurface(surfaceId).dataModel,
      path,
      fileInfos.length === 1 ? fileInfos[0] : fileInfos
    );

    // 触发重建以更新 UI
    (this.processor as any).rebuildComponentTree((this.processor as any).getOrCreateSurface(surfaceId));
  }

  #renderFileList() {
    if (this._selectedFiles.length === 0) {
      return nothing;
    }
    return html`
      <div class="file-list">
        ${this._selectedFiles.map(
          (file, index) => html`
            <div class="file-item">
              <span class="file-name">${file.name}</span>
              <button
                class="remove-button"
                @click=${() => this.#removeFile(index)}
              >
                ×
              </button>
            </div>
          `
        )}
      </div>
    `;
  }

  #renderProgressBar() {
    if (this._uploadProgress < 0) {
      return nothing;
    }
    return html`
      <div class="progress-bar">
        <div
          class="progress-fill"
          style="width: ${this._uploadProgress}%"
        ></div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="file-upload-container">
        <div class="file-input-wrapper">
          <button class="upload-button" @click=${this.#triggerClick}>
            <slot>选择文件</slot>
          </button>
          <input
            type="file"
            ?multiple=${this.multiple}
            accept=${this.accept}
            ?webkitdirectory=${this.directory}
            @change=${this.#handleFileSelect}
          />
        </div>
        ${this.#renderFileList()}
        ${this.#renderProgressBar()}
      </div>
    `;
  }
}
