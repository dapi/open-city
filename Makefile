PYTHON ?= .venv/bin/python

deps:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

validate:
	$(PYTHON) scripts/validate/repository.py

chat-archive-markdown:
	python3 scripts/chatgpt-export/convert-to-markdown.py

chat-archive-markdown-check:
	python3 scripts/chatgpt-export/convert-to-markdown.py --check

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

site:
	$(PYTHON) platform/publishing/build_site.py

site-preview:
	$(PYTHON) platform/publishing/build_site.py --include-drafts

site-serve: site-preview
	$(PYTHON) -m http.server 4173 --bind 127.0.0.1 --directory var/output/site

PUBLIC_SITE ?= ../opencitystudio.ru

site-sync-content:
	$(PYTHON) platform/publishing/build_site.py --sync-characters-to $(PUBLIC_SITE)

site-sync-characters: site-sync-content

review-submit:
	$(PYTHON) platform/publishing/review_bot.py submit $(ISSUE)

review-submit-script:
	$(PYTHON) platform/publishing/review_bot.py submit-script $(ISSUE)

review-submit-retro:
	$(PYTHON) platform/publishing/review_bot.py submit-retro $(ISSUE)

review-run:
	$(PYTHON) platform/publishing/review_bot.py run

review-discover:
	$(PYTHON) platform/publishing/review_bot.py discover

review-configure-private:
	$(PYTHON) platform/publishing/review_bot.py configure-private

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
