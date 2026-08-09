PYTHON ?= .venv/bin/python

deps:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

validate:
	$(PYTHON) scripts/validate/repository.py

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

voices:
	$(PYTHON) platform/voice/generate.py --list-voices --api-key ${XI_API_KEY}

generate:
	$(PYTHON) platform/voice/generate.py productions/episodes/pilot-v1.2/script/timeline.json \
  --api-key ${XI_API_KEY} \
  --speaker-map productions/episodes/pilot-v1.2/audio/speaker-map.json \
  --model eleven_multilingual_v2 \
  --voice-settings stability=0.45,similarity_boost=0.9,style=0.25,use_speaker_boost=true \
  --srt \
  --output-dir var/output/pilot-v1.2 \
  --cache-dir var/cache/voice
