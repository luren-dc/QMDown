<div align="center">
    <a>
        <img src="https://socialify.git.ci/luren-dc/QMDown/image?description=1&font=Source%20Code%20Pro&language=1&logo=https%3A%2F%2Fy.qq.com%2Fmediastyle%2Fmod%2Fmobile%2Fimg%2Flogo.svg&name=1&pattern=Overlapping%20Hexagons&theme=Auto"/>
    </a>
    <a href="https://www.python.org">
        <img src="https://img.shields.io/badge/Python-3.10|3.11|3.12-blue" alt="Python"/>
    </a>
    <a href="https://github.com/luren-dc/QMDown?tab=MIT-1-ov-file">
        <img src="https://img.shields.io/github/license/luren-dc/QMDown" alt="GitHub license"/>
    </a>
    <a href="https://github.com/luren-dc/QMDown/stargazers">
        <img src="https://img.shields.io/github/stars/luren-dc/QMDown?color=yellow&label=Github%20Stars" alt="STARS"/>
    </a>
    <a href="https://gitmoji.dev"><img alt="Gitmoji" src="https://img.shields.io/badge/gitmoji-%20😜%20😍-FFDD67?style=flat-square"></a>
    <a href="https://github.com/astral-sh/uv">
      <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv"/>
    </a>
</div>

---

> [!NOTE]
> 重构中

**欢迎向本项目提出[Issues](https://github.com/luren-dc/QMDown/issues),贡献[Pull Requests](https://github.com/luren-dc/QMDown/pulls)**

> [!IMPORTANT]
> 本仓库的所有内容仅供学习和参考之用，禁止用于商业用途
>
> **音乐平台不易，请尊重版权，支持正版。**

## 安装

### pip/pipx/uv 安装

```bash
# 通过 pip
pip install QMDown
# 使用 pipx
pipx install QMDown
# 或者使用 uv
uv tool install QMDown
```

### 体验 main 分支最新特性

```bash
# 通过 pip
pip install git+https://github.com/luren-dc/QMDown@main
# 通过 pipx
pipx install git+https://github.com/luren-dc/QMDown@main
# 通过 uv
uv tool install git+https://github.com/luren-dc/QMDown.git@main
```

## 特色

- 支持登录
  - [x] Cookies
  - [x] 二维码
    - [x] QQ
    - [x] WX
  - [x] 手机号
- 支持类型
  - [x] 歌手
  - [x] 专辑
  - [x] 歌单
  - [x] 歌曲
  - [x] 排行榜
  - [x] 普通歌词
  - [x] 翻译歌词
  - [x] 罗马歌词
- 支持音质
  - [x] 臻品母带
  - [x] 臻品音质
  - [x] 臻品全景声
  - [x] flac
  - [x] OGG
  - [x] MP3
  - [x] AAC(M4A)

### 已支持下载类型

| 类型   | 示例链接                                                                                                                                 |
|------|--------------------------------------------------------------------------------------------------------------------------------------|
| base | `https://c6.y.qq.com/base/fcgi-bin/u?__=jXIuFz8tBzpA`                                                                                |
| 歌曲   | `https://y.qq.com/n/ryqq/songDetail/004Ti8rT003TaZ` <br/> `https://i.y.qq.com/v8/playsong.html?songmid=004UMhHW33BWSk`               |
| 歌单   | `https://y.qq.com/n/ryqq/playlist/1374105607` <br/> `https://i.y.qq.com/n2/m/share/details/taoge.html?id=7524170477`                 |
| 专辑   | `https://y.qq.com/n/ryqq/albumDetail/003dYC933CfoSi` <br/> `https://i.y.qq.com/n2/m/share/details/album.html?albumId=50967596`       |
| 排行榜  | `https://y.qq.com/n/ryqq/toplist/3` <br/> `https://i.y.qq.com/n2/m/share/details/toplist.html?id=26`                                 |
| 歌手   | `https://y.qq.com/n/ryqq/singer/001BLpXF2DyJe2` <br/> `https://i.y.qq.com/n2/m/share/profile_v2/index.html?singermid=0025NhlN2yWrP4` |

## 基本使用

```console
Usage: QMDown [OPTIONS] URLS...

 QQ 音乐解析/下载工具

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    urls      URLS...  QQ 音乐链接  支持多个链接,可带有其他文本,会自动提取 [required]                                         │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --no-progress            禁用进度条显示                                                                                        │
│ --no-color               禁用彩色输出                                                                                          │
│ --debug                  启用调试日志输出                                                                                      │
│ --version      -v        输出版本信息                                                                                          │
│ --help         -h        Show this message and exit.                                                                           │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Download 下载 ────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --output       -o      DIRECTORY                                     下载文件存储目录 [default: /root/Python/QMDown]           │
│ --num-workers  -n      INTEGER RANGE [x>=1]                          并发下载协程数量 [default: 8]                             │
│ --quality      -q      [130|120|110|100|90|80|70|60|50|40|30|20|10]  首选音频品质 [default: 50]                                │
│ --overwrite    -w                                                    覆盖已存在文件                                            │
│ --max-retries  -r      INTEGER RANGE [x>=0]                          下载失败重试次数 [default: 3]                             │
│ --timeout      -t      INTEGER RANGE [x>=0]                          下载超时时间 [default: 15]                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Lyric 歌词 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --lyric                   下载原始歌词文件                                                                                     │
│ --trans                   下载双语翻译歌词(需配合`--lyric`使用)                                                                │
│ --roma                    下载罗马音歌词(需配合`--lyric`使用)                                                                  │
│ --no-embed-lyric          禁用歌词文件嵌入                                                                                     │
│ --no-del-lyric            禁用嵌入歌词文件后删除                                                                               │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Metadata 元数据 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --no-metadata          禁用元数据添加                                                                                          │
│ --no-cover             禁用专辑封面嵌入                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Authentication 认证管理 ──────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --cookies  -c      MUSICID:MUSICKEY  QQ音乐Cookie凭证(从浏览器开发者工具获取 `musicid` 和 `musickey`,拼接为 `musicid:musickey… │
│                                      格式)                                                                                     │
│ --login            [QQ|WX|PHONE]     第三方登录方式                                                                            │
│ --load             FILE              加载 Cookies 文件路径                                                                     │
│ --save             FILE              持久化 Cookies 文件路径                                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### 音质说明

<details>
<summary>点击展开</summary>

| 音频格式     | code |
|----------|------|
| MASTER   | 130  |
| ATMOS_2  | 120  |
| ATMOS_51 | 110  |
| FLAC     | 100  |
| OGG_640  | 90   |
| OGG_320  | 80   |
| MP3_320  | 70   |
| OGG_192  | 60   |
| MP3_128  | 50   |
| OGG_96   | 40   |
| ACC_192  | 30   |
| ACC_96   | 20   |
| ACC_48   | 10   |

</details>

## Licence

本项目基于 **[MIT License](https://github.com/luren-dc/QMDown?tab=MIT-1-ov-file)** 许可证发行。

## 免责声明

由于使用本项目产生的包括由于本协议或由于使用或无法使用本项目而引起的任何性质的任何直接、间接、特殊、偶然或结果性损害（包括但不限于因商誉损失、停工、计算机故障或故障引起的损害赔偿，或任何及所有其他商业损害或损失）由使用者负责

## 贡献者

[![Contributor](https://contrib.rocks/image?repo=luren-dc/QMDown)](https://github.com/luren-dc/QMDown/graphs/contributors)
