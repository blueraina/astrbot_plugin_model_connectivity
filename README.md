# AstrBot 模型连通性状态图插件

这个插件会枚举当前 AstrBot WebUI 中已打开的聊天模型，并检测这些模型的连通性，最后发送一张类似状态页的看板图片。

## 命令

- `/modeltest`
- `/模型连通性`
- `/modelstatus`
- `/模型状态`
- `/modelstatusoff`
- `/取消模型状态推送`
- `/modelskiprefresh`
- `/刷新模型候选`

## 显示内容

- Provider 名称、类型、ID
- 每个模型的当前连通状态：正常、较慢、错误
- 对话往返耗时
- 周成功次数，格式为 `成功次数/总测试次数`
- 最近若干次检测历史条
- 周可用率
- 默认本地生成 PNG 图片，不依赖 AstrBot 远端 t2i 服务
- 支持 `image_scale` 高清输出，默认 2 倍
- 支持白天/夜间主题，默认按时间自动切换
- 支持后台定时自动检测，自动更新历史和周统计
- 支持后台定时发送最近一次状态图，不会触发新的检测
- 支持从 `providerUtils.js` 读取 Provider 图标映射，并在本地 PNG 中显示头像
- 内置 `logo.png`，用于 AstrBot 插件市场头像展示

## 安装

把本目录放到 AstrBot 的插件目录中，例如：

```text
data/plugins/astrbot_plugin_model_connectivity
```

然后在 AstrBot 插件管理中启用插件，或重启 AstrBot。

## 注意

插件会真实调用模型做一次轻量对话探测，可能产生调用额度消耗。默认只检测 WebUI 中开关为打开的已配置模型，灰色关闭的模型会跳过。

如果你想恢复旧行为，检测 Provider 暴露出的模型列表，可以把 `detect_enabled_models_only` 设为 `false`；这时 `max_models_per_provider` 可用于限制每个 Provider 最多检测多少个模型。

默认 `render_backend = local`，插件会用 Pillow 在本地生成 PNG，避免 AstrBot 远端 HTML 转图服务不可用时失败。如果想继续使用 AstrBot 自带 `html_render`，可以把 `render_backend` 设为 `remote`。

主题相关配置：

- `theme_mode`：`auto`、`dark`、`light`，默认 `auto`。
- `day_mode_start_hour` / `day_mode_end_hour`：自动白天模式的时间段，例如 `8` 到 `18` 表示 08:00-18:00 使用白天模式。

定时检测相关配置：

- `auto_check_interval_min_hours`：定时自动检测的最小间隔小时，`0` 表示关闭。
- `auto_check_interval_max_hours`：定时自动检测的最大间隔小时，例如最小 `2`、最大 `5` 表示每轮随机等待 `2-5` 小时。
- `auto_check_run_on_start`：插件启动后是否立即自动检测一次。

后台定时检测只更新历史记录、周成功次数和可用率，不会主动往聊天里发送图片。

定时发送状态图相关配置：

- `auto_status_send_interval_hours`：每隔多少小时发送一次最近状态图，`0` 表示关闭。
- `auto_status_remember_command_session`：是否自动记住执行命令的会话，默认开启。需要发到哪个群或私聊，就先在那里执行一次 `/modeltest` 或 `/modelstatus`。

`/modelstatus` 和定时发送都只读取最近一次检测结果并渲染图片，不会调用模型。第一次使用前请先执行一次 `/modeltest`，或开启定时自动检测让插件产生最新状态。

在某个群聊/私聊中执行 `/modelstatusoff` 或 `/取消模型状态推送`，可以取消该会话的自动推送；不影响其他群聊/私聊，也不关闭全局定时发送。

跳过模型配置：

- `skip_models`：填写不参与检测的模型，多个值可用英文逗号或换行分隔。

支持完整值形如 `openai_1/gpt-5.4`，也支持只填模型名如 `gpt-5.4`。

可以执行 `/modelskiprefresh` 或 `/刷新模型候选` 查看当前可填写的候选值。

如果 Provider 的模型配置被手动改过，插件会从 `model_config`、`models`、`enabled_models`、最近一次检测报告等位置兜底提取候选。

并发控制分为两层：

- `concurrency`：全局最大并发数，所有 Provider 的所有模型一起共享，等价于 m。
- `provider_concurrency`：单个 Provider 内最大并发数，等价于 n。

例如 `concurrency = 6`、`provider_concurrency = 2` 时，插件全局最多同时检测 6 个模型，并且每个 Provider 内最多同时检测 2 个模型。
