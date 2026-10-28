"""路由认证由 app.auth.policy.policy 在依赖里执行。

原先的 EnforceAuthMiddleware 早于路由依赖，读不到 route_policy，实际不会校验。
关闭认证时的演示用户，以及生产环境禁止关闭认证，改在 apply_route_policy 里处理。
"""
