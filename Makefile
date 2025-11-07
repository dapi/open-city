deps:
	pip3 install requests pydub numpy


voices:
	python3 generate_voice_v2.py --list-voices --api-key ${XI_API_KEY}
generate:
	python3 generate_voice_v2.py ./voice_script_v1.2_extended.json \
  --api-key ${XI_API_KEY} \
  --speaker-map speakers.json \
  --model eleven_multilingual_v2 \
  --voice-settings stability=0.45,similarity_boost=0.9,style=0.25,use_speaker_boost=true \
  --srt
