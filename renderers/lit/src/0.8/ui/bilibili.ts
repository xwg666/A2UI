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
import * as Primitives from "@a2ui/web_core/types/primitives";
import { classMap } from "lit/directives/class-map.js";
import { styleMap } from "lit/directives/style-map.js";
import { structuralStyles } from "./styles.js";

@customElement("a2ui-bilibili")
export class Bilibili extends Root {
  @property()
  accessor bvid: Primitives.StringValue | null = null;

  @property()
  accessor page: number = 1;

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
      }

      .bilibili-container {
        position: relative;
        width: 100%;
        padding-bottom: 56.25%; /* 16:9 比例 */
        height: 0;
        overflow: hidden;
      }

      iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: none;
      }
    `,
  ];

  #extractBvid(url: string): string | null {
    // 从各种 Bilibili URL 格式中提取 BV 号
    const patterns = [
      /video\/(BV[\w]+)/,  // /video/BVxxx
      /bvid=(BV[\w]+)/i,   // bvid=BVxxx
      /^(BV[\w]+)$/,       // 纯 BV 号
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) {
        return match[1];
      }
    }
    return null;
  }

  #getBvid(): string | null {
    if (!this.bvid) {
      return null;
    }

    if (typeof this.bvid === "string") {
      return this.#extractBvid(this.bvid);
    }

    if (typeof this.bvid === "object") {
      if ("literalString" in this.bvid && this.bvid.literalString) {
        return this.#extractBvid(this.bvid.literalString);
      }
      if ("literal" in this.bvid && this.bvid.literal) {
        return this.#extractBvid(this.bvid.literal);
      }
      if ("path" in this.bvid && this.bvid.path && this.processor && this.component) {
        const value = this.processor.getData(
          this.component,
          this.bvid.path,
          this.surfaceId ?? "default"
        );
        if (typeof value === "string") {
          return this.#extractBvid(value);
        }
      }
    }

    return null;
  }

  #renderIframe() {
    const bvid = this.#getBvid();

    if (!bvid) {
      return html`<div class="error">无效的 Bilibili 视频链接</div>`;
    }

    const embedUrl = `https://player.bilibili.com/player.html?bvid=${bvid}&page=${this.page}&high_quality=1&danmaku=0`;

    return html`
      <div class="bilibili-container">
        <iframe
          src=${embedUrl}
          scrolling="no"
          border="0"
          frameborder="no"
          framespacing="0"
          allowfullscreen
        ></iframe>
      </div>
    `;
  }

  render() {
    const bilibiliClasses = (this.theme.components as any).Bilibili || {};
    const bilibiliStyles = (this.theme.additionalStyles as any)?.Bilibili;
    return html`<section
      class=${classMap(bilibiliClasses)}
      style=${bilibiliStyles ? styleMap(bilibiliStyles) : nothing}
    >
      ${this.#renderIframe()}
    </section>`;
  }
}
