# 作者资料链接图标

这些文件只用于标识作者资料页和清单中指向相应服务的链接。图标随网站一起发布，不向第三方 CDN 请求图标或字体。网页的可访问名称与提示文字由 `author-pages.lua` 生成；PDF 和 Markdown 继续保留文字链接。

## 来源

取得日期：2026-10-21。品牌标记的商标权仍属于各自权利人；本项目不因此获得对这些商标的所有权，也不表示受到相关服务的认可。

| 文件 | 原始来源 | 保留方式 |
| --- | --- | --- |
| `orcid.svg` | [ORCID 官方源码中的 id-icon.svg](https://github.com/ORCID/ORCID-Source/blob/main/orcid-web/src/main/webapp/static/img/id-icon.svg) | 官方静态 iD 图标原文件，`viewBox="0 0 256 256"`，保留绿色 `#A6CE39` 和白色 |
| `github.svg`、`github-dark.svg` | [GitHub 官方 Logo Toolkit](https://brand.github.com/foundations/logo) 的 [GitHub_Logos.zip](https://brand.github.com/GitHub_Logos.zip)，`GitHub Logos/SVG/GitHub_Invertocat_Black.svg` 与 `GitHub_Invertocat_White.svg` | 官方 Invertocat 原文件，`viewBox="0 0 98 96"`；明暗主题使用官方黑／白版本 |
| `google-scholar.png` | [Google Scholar 官方 favicon.ico](https://scholar.google.com/favicon.ico) | 从 ICO 中直接取出原有 48 × 48 PNG 字节，不重绘、裁切或缩放；适合以 24px 展示 |
| `email.svg`、`website.svg`、`institution.svg` | 为本项目绘制的信封、地球与机构建筑几何图形 | `viewBox="0 0 24 24"`，使用 `currentColor` 线条，随网页主题配色 |

GitHub 的官方品牌规则允许把其标记用作链接到 GitHub 个人主页或项目的社交入口。保持官方图形、比例及黑／白配色，不把它用作本项目自己的标志。内联时为避免重复 DOM ID 而调整 SVG 的内部引用 ID，不改变图形。

ORCID™、ORCID logo 和 iD logo 是 ORCID, Inc. 的商标。参见 [ORCID 品牌指南](https://info.orcid.org/brand-guidelines/)及 [iD 显示指南](https://info.orcid.org/documentation/integration-guide/orcid-id-display-guidelines/)。这里保留官方公开源码中的既有静态图标作为资料链接；作者资料是手工提供的，不表示本项目已通过 ORCID OAuth 认证其身份。若将来接入 ORCID 认证，应同时复核当时的认证状态显示要求和官方资产。

Google Scholar 图标取自其官方站点，不是第三方重绘，也不属于本项目原创图形。使用时保留原图，不做整体反色；通过入口的边框、背景和焦点轮廓适配明暗主题。

## 文件校验

以下 SHA-256 对应取得时的原文件，便于检查资产是否意外变更：

```text
orcid.svg          26483c4d9c32c10f7d5a7dc895ede560696336d336dac582dc3c6a8b94500919
github.svg         b307162d008fe9340c9012cc322629434ce23c2c20a1b13ae3e222efc76e4710e
github-dark.svg    ccd84c89b1056345608fc3489357f8acc7397e49a3cdc2d418b6c8016911d47b
google-scholar.png 697cb6edfc2c557b71cf2ad7f5f940e4b631d21e5e33967546715ef349272b4b
```
