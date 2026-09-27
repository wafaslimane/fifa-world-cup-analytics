PY ?= python

.PHONY: install extract pipeline test app all clean

install:
	$(PY) -m pip install -r requirements.txt

extract:            ## Télécharge les CSV sources dans data/raw
	$(PY) -m src.fifa_pipeline.extract

pipeline:           ## Nettoyage + contrôles qualité + chargement DuckDB
	$(PY) -m src.fifa_pipeline.run

test:
	$(PY) -m pytest -q

app:
	streamlit run app/streamlit_app.py

all: pipeline test

clean:
	rm -rf data/processed data/warehouse
