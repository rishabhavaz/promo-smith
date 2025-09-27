python -m venv .venv && source .venv/bin/activate  
pip install --upgrade pip setuptools wheel && pip install -r slack-promo-bot/requirements.txt  
python slack-promo-bot/app.py
