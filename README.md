# MediaDownloadBot

[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&link=https://t.me/QuartzMediaBot)](https://t.me/QuartzMediaBot)

Telegram bot to download media from various sources

To do:
- [x] Twitter videos
- [x] Pinterest videos
- [x] Instagram videos
- [x] TikTok videos
- [x] VK clips

## K8s Deployment

Create a secret with bot's token:
```bash
kubectl create secret generic mediadownloadbot-secret --from-literal=TOKEN=...
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```
