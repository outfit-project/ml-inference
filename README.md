# ML inference worker

Processes garment photos in the background using Marqo FashionCLIP through OpenCLIP. Predicts category, subtype, style and a color label, then sends the metadata and a normalized 512-dimensional image embedding to wardrobe.

[Wardrobe contracts](https://github.com/outfit-project/wardrobe-service#internal-contracts) · [Model](https://huggingface.co/Marqo/marqo-fashionCLIP) · [Run all services](https://github.com/outfit-project/api-gateway#run-all-repositories)

## Start this repository

Requirements: Docker with Compose 2.20+, internet access for the first model download, and enough memory for CPU inference (allow about 6 GB for the complete application). From this repository:

```bash
cp .env.example .env
docker network create vestis-services
docker compose up --build -d --wait --wait-timeout 900
```

PowerShell also supports `cp`. Copy the example only for initial setup; reconcile an existing `.env` instead of replacing it. Create the shared network once, skipping this step if it exists. `VESTIS_NETWORK` selects another pre-created network. Replace example secrets for deployment.

This starts only ML, an isolated Redis and MinIO. The worker loads the real model, becomes ready and waits for tasks; there is no HTTP port. No parent files or other checkouts are needed to start it. The Redis, photo storage and model cache use persistent project-specific volumes; `docker compose down` preserves them. Isolated mode does not fabricate a wardrobe API or complete real photo jobs without a reachable callback.

To process uploads from a separately running wardrobe, put both projects on the same network and set these ML `.env` values:

```dotenv
REDIS_URL=redis://vestis-wardrobe-redis:6379/0
MINIO_ENDPOINT=http://vestis-wardrobe-minio:9000
WARDROBE_PROCESSING_URL=http://outfit_wardrobe_api:8000/items/processing
```

Copy `ML_SERVICE_TOKEN`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` and `ML_TASKS_QUEUE` from wardrobe, then run `docker compose up -d`. The worker now consumes wardrobe's queue and storage; its isolated Redis/MinIO remain idle. Run only one worker against a given wardrobe queue.

## Processing flow

The worker has **no HTTP API**. It consumes the wardrobe Redis list, reads the original photo from S3 and reports results through `PATCH /items/processing` with `X-Service-Token`.

1. Load model weights and cache garment/style/color text features at startup.
2. Recover abandoned in-flight tasks, then consume one task at a time.
3. Mark the item `processing`, fetch/decode/validate the photo and compute inference.
4. Validate the embedding and send complete metadata with `processing_status: ready`.
5. Acknowledge the queue task only after processing/callback handling completes.

The event envelope is documented in [wardrobe](https://github.com/outfit-project/wardrobe-service#internal-contracts). Its `data.image_url` is an S3 object key, not a URL. The worker uses the same bucket and credentials as wardrobe and has no direct database access.

## Model and vocabulary

Default model: `hf-hub:Marqo/marqo-fashionCLIP`, CPU inference. The first startup downloads weights; subsequent starts reuse the `model-cache` volume mounted at `/models` through `HF_HOME`.

Zero-shot labels are selected against fixed text prompts in [vocabulary.py](src/inference/model_inference/vocabulary.py):

| Category | Subtypes |
| --- | --- |
| `top` | t-shirt, shirt, blouse, sweater, hoodie, tank top, polo shirt |
| `bottom` | jeans, trousers, shorts, skirt, leggings |
| `outerwear` | coat, jacket, blazer, cardigan, vest |
| `shoes` | sneakers, boots, sandals, heels, loafers, dress shoes |
| `accessory` | bag, hat, scarf, belt, sunglasses, watch |

Styles: `casual`, `formal`, `sport`, `streetwear`. The color vocabulary has 13 labels with representative hex values. Colors are selected labels, not measured fabric swatches. Similarities are not calibrated confidence scores.

Use clear photos containing one garment. This version does not segment multiple garments or support dresses/full-body outfits. Replacing the model requires matching its output dimension with wardrobe and checking vocabulary behavior.

## Queue reliability and failures

`BLMOVE` moves a task from `ml_tasks` to `ml_tasks:processing`. Successful handling removes the raw task from the processing list. Startup and ambiguous consume errors recover in-flight entries before the next consume.

Run **one replica**: recovery uses a shared processing list and is not designed for concurrent worker ownership. Processing is at least once; a crash can repeat inference/callbacks. Failed-state writes, dead-letter publication and acknowledgment are separate operations.

Transient processing errors get up to `WORKER_MAX_RETRIES` retries after the first attempt: the default is four total attempts, with linear backoff of 500, 1000 and 1500 milliseconds. Permanent errors stop immediately. A failed item is reported to wardrobe and the raw task is appended to `ml_tasks_dlq`. Malformed envelopes go directly to that list. Callback/infrastructure failures leave work recoverable rather than silently acknowledging it. A callback 404 is tolerated when the item has been deleted.

Use the owner's retry API for failed items after fixing the cause. No automatic dead-letter replay command is provided.

## Configuration

Settings: [src/config/settings.py](src/config/settings.py). Compose reads the repository's `.env` and passes its explicit environment to the worker.

| Variable | Value / purpose |
| --- | --- |
| `REDIS_URL` | Isolated: `redis://ml-redis:6379/0`; connected: `redis://vestis-wardrobe-redis:6379/0` |
| `ML_TASKS_QUEUE`, `ML_TASKS_DLQ` | `ml_tasks`, `ml_tasks_dlq` |
| `WARDROBE_PROCESSING_URL` | `http://outfit_wardrobe_api:8000/items/processing` |
| `ML_SERVICE_TOKEN` | Same callback secret as wardrobe |
| `MINIO_ENDPOINT` | Isolated: `http://ml-minio:9000`; connected: `http://vestis-wardrobe-minio:9000` |
| `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` | Shared photo-store configuration |
| `OPENCLIP_MODEL_NAME` | `hf-hub:Marqo/marqo-fashionCLIP` |
| `OPENCLIP_PRETRAINED` | Empty for the default Hugging Face model |
| `INFERENCE_DEVICE` | `cpu`; changing this alone does not configure GPU support |
| `EMBEDDING_DIM` | `512` |
| `HF_HOME` | `/models`, persistent Hugging Face cache |
| `MODEL_LOAD_ON_STARTUP` | Application default `true`; required by this entry point |
| `REDIS_BLPOP_TIMEOUT_SEC` | Application default `5`; blocking BLMOVE timeout despite legacy name |
| `WORKER_MAX_RETRIES`, `WORKER_RETRY_BACKOFF_MS` | Application defaults `3`, `500` |

The model, queue, callback, storage and retry settings above are forwarded by the local Compose file. `MODEL_LOAD_ON_STARTUP` is fixed to `true` for this entry point. `WARDROBE_EMBEDDING_URL` is a native-development legacy fallback; Compose sets the processing URL explicitly.

## Run and inspect

From this repository, in isolated mode:

```bash
docker compose ps
docker compose logs -f ml-inference
docker compose exec -T ml-redis redis-cli LLEN ml_tasks
docker compose exec -T ml-redis redis-cli LLEN ml_tasks:processing
docker compose exec -T ml-redis redis-cli LLEN ml_tasks_dlq
```

The Linux container runs `python -m src.bootstrap.entrypoint`. Its `/tmp/worker-ready` file is created after model/worker initialization and removed on shutdown. This is a startup marker, not a continuous dependency probe: Redis/callback outages can leave the container healthy while the loop retries. Allow time and memory for the first model load. The entry point uses Unix signal handlers; use the container on Windows.

## Checks

Use a separate Python 3.12 environment: Torch/NumPy dependencies differ from other services. From this repository:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q src
```

Unit tests use deterministic inference doubles and test queue/callback handling, including lost consume replies and deleted-item callbacks. They do not establish model quality. For a real check, connect wardrobe, upload one garment photo through its API and wait for `ready` metadata and a 512-dimensional embedding. In connected mode, inspect queue lengths with `docker compose exec -T wardrobe-redis ...` from the wardrobe repository.
