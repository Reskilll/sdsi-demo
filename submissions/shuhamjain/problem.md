Your Round 1 details

Problem statement
PS3: URL Shortener with Analytics

Shorten URLs into short codes, resolve them, and track how each link is used.

What your code is judged on

M1 Shorten a URL (optional custom alias and expiry) into a base62 code of 6–8 characters.
M2 Resolve a code: redirect (302), expired (410), unknown (404).
M3 Validate URLs: http/https only, reject malformed URLs and javascript:-style schemes.
M4 Shortening the same URL twice returns the same code (idempotent), unless a custom alias is given.
M5 Stats per code: total clicks, clicks per day, last accessed time.
Also judged on: Functional correctness · Code quality and design · Testing · Documentation and runnability (README) · AI collaboration effectiveness (PROMPTS.md) · Security and robustness · Git hygiene · Performance awareness · Error handling and input validation

Your code is also checked against edge cases that aren’t listed here: think them through yourself.

Anything you build on top as a stretch or bonus also carries weight in your selection.