echo "downloading segments ..."
dir="$(python download.py $1)"
cd "$dir"
echo "Joining audio segments ..."
cat $(ls audio_segment_* | grep -oE '[0-9]+' | sort -n | while read -r num; do echo audio_segment_$num.ts; done) > audio.ts
echo "joining video segments..."
cat $(ls video_segment_* | grep -oE '[0-9]+' | sort -n | while read -r num; do echo video_segment_$num.ts; done) > video.ts
echo "Merging Audio and Video. Transcoding to final cut..."
ffmpeg -i video.ts -i audio.ts -vcodec h264 -acodec aac "$dir".mp4
rm audio_segment* video_segment*