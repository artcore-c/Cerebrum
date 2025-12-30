### systemd Service

A sample systemd unit file is provided at:

   [cerebrum-backend/`cerebrum-backend.service.example`](../../cerebrum-backend/cerebrum-backend.service.example)

Copy it to `/etc/systemd/system/cerebrum-backend.service`,
adjust paths and user names, then enable it:

```bash
sudo cp cerebrum-backend.service.example /etc/systemd/system/cerebrum-backend.service
sudo systemctl daemon-reload
sudo systemctl enable cerebrum-backend
sudo systemctl start cerebrum-backend
```

For detailed systemd configuration information:  
📙 See: [Systemd Service Configuration](../../cerebrum-backend/README.md#systemd-service-configuration)