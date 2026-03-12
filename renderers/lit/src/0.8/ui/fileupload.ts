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

  @state()
  private accessor _previewUrls: Map<string, string> = new Map();

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

      .file-preview {
        margin-top: 8px;
        padding: 8px;
        background-color: #fafafa;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
      }

      .preview-image {
        max-width: 200px;
        max-height: 200px;
        width: auto;
        height: auto;
        border-radius: 4px;
        display: block;
      }

      .preview-document {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px;
        background-color: #f5f5f5;
        border-radius: 4px;
      }

      .preview-icon {
        font-size: 24px;
      }

      .preview-info {
        display: flex;
        flex-direction: column;
        font-size: 12px;
      }

      .preview-type {
        color: #666;
        font-size: 11px;
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
      // 生成预览
      this.#generatePreviews();
      // 将文件信息写入 data model
      this.#updateDataModel();
    }
  }

  #generatePreviews() {
    // 清理旧的预览 URL
    this._previewUrls.forEach(url => URL.revokeObjectURL(url));
    this._previewUrls.clear();

    this._selectedFiles.forEach(file => {
      if (file.type.startsWith('image/')) {
        // 图片文件：创建 Object URL
        const url = URL.createObjectURL(file);
        this._previewUrls.set(file.name, url);
      }
      // 其他文件类型不需要预览 URL，会在渲染时显示图标
    });
  }

  #getFileIcon(file: File): string {
    if (file.type.startsWith('image/')) return '🖼️';
    if (file.type.includes('pdf')) return '📄';
    if (file.type.includes('word') || file.type.includes('document')) return '📝';
    if (file.type.includes('excel') || file.type.includes('sheet')) return '📊';
    if (file.type.includes('powerpoint') || file.type.includes('presentation')) return '📽️';
    if (file.type.includes('text')) return '📃';
    if (file.type.includes('zip') || file.type.includes('compressed')) return '📦';
    return '📎';
  }

  #formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  #removeFile(index: number) {
    const removedFile = this._selectedFiles[index];
    // 清理该文件的预览 URL
    if (removedFile && this._previewUrls.has(removedFile.name)) {
      URL.revokeObjectURL(this._previewUrls.get(removedFile.name)!);
      this._previewUrls.delete(removedFile.name);
    }
    this._selectedFiles = this._selectedFiles.filter((_, i) => i !== index);
    this.#updateDataModel();
  }

  #updateDataModel() {
    if (!this.processor || !this.component) {
      console.log("[FileUpload] Cannot update data model: missing processor or component");
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
    const path = "/files";  // 使用绝对路径

    console.log("[FileUpload] Updating data model:", { path, fileInfos, component: this.component.id });

    // 使用 processor.setData 更新数据
    this.processor.setData(
      this.component,
      path,
      fileInfos.length === 1 ? fileInfos[0] : fileInfos,
      surfaceId
    );
  }

  #renderFilePreview(file: File) {
    if (file.type.startsWith('image/')) {
      const previewUrl = this._previewUrls.get(file.name);
      if (previewUrl) {
        return html`
          <div class="file-preview">
            <img class="preview-image" src=${previewUrl} alt=${file.name} />
          </div>
        `;
      }
    }
    
    // 文档或其他文件类型显示图标和信息
    return html`
      <div class="file-preview">
        <div class="preview-document">
          <span class="preview-icon">${this.#getFileIcon(file)}</span>
          <div class="preview-info">
            <span>${file.name}</span>
            <span class="preview-type">${this.#formatFileSize(file.size)} · ${file.type || '未知类型'}</span>
          </div>
        </div>
      </div>
    `;
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
            ${this.#renderFilePreview(file)}
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
