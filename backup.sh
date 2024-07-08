rm -rf Documents/com~apple~CloudDocs/FL/Bounces/*
cp -v -n -r ~/BEATSTARS/Bounces/* /Users/matusbolecek/Library/Mobile\ Documents/com~apple~CloudDocs/FL/Bounces/
cp -v -r -n /Volumes/wd/BEATS/* /Users/matusbolecek/Library/Mobile\ Documents/com~apple~CloudDocs/FL/Projects/

current_date=$(date +"%Y-%m-%d")
echo "Backup: $current_date" >> backups.txt
