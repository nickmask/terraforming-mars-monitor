# terraforming-mars-monitor


# Check monitor output
tail -f /home/nrmaskell/terraforming-mars-monitor/monitor.log

# Check update script logs
tail -f /home/nrmaskell/terraforming-mars-monitor/autoupdate.log

# Check startup logs
tail -f /home/nrmaskell/terraforming-mars-monitor/startup.log

# Update env variables
sudo nano /etc/systemd/system/terraforming-mars-monitor.service

## Reload the systemd daemon
sudo systemctl daemon-reload

## Restart your service
sudo systemctl restart terraforming-mars-monitor

## Check the status
sudo systemctl status terraforming-mars-monitor


EhmZzFcWJQv9Lshl5twtn5@g.us