1. **create environment**

```bash
conda create -n medgemma python=3.12 -y
conda activate medgemma                                        
```

2. **install vllm & Dependencies**

```bash
pip install vllm huggingface_hub openai fastapi uvicorn python-multipart scikit-learn
```

3. **huggingface login**

```bash
huggingface-cli login
```
the paste your HF_TOKEN 


4. **Deploy medgemma-1.5-4b-it on port 8000**

vllm serve google/medgemma-1.5-4b-it \
  --trust-remote-code \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --host 127.0.0.1 \
  --port 8000 \
  --gpu-memory-utilization 0.77


5. **Deploy medsiglip on port 9000**

python medsiglip_server.py


6. **NGINX**

```bash
sudo apt update
sudo apt install nginx -y
```

```bash
sudo nano /etc/nginx/sites-available/default
```

Limit to 5 requests per second per IP

```bash
limit_req_zone $binary_remote_addr zone=hackathon_limit:10m rate=5r/s;

server {
    # Nginx NOW LISTENS ON YOUR PUBLIC PORT
    listen 8888; 
    
    # Allow large uploads
    client_max_body_size 10M;

    # --- ROUTE 1: MedGemma (LLM) ---
    # Public: http://<IP>:8888/v1/...
    location /v1/ {
        limit_req zone=hackathon_limit burst=10 nodelay;
        
        # Forward to vLLM on INTERNAL port 8000
        proxy_pass http://127.0.0.1:8000;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Streaming settings
        proxy_buffering off;
    }

    # --- ROUTE 2: MedSigLIP (Vision) ---
    # Public: http://<IP>:8888/analyze
    location /analyze {
        limit_req zone=hackathon_limit burst=5 nodelay;
        
        # Forward to Python on INTERNAL port 9000
        proxy_pass http://127.0.0.1:9000;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```



```bash
sudo systemctl restart nginx
```


6. **AUTOSTART**



```bash
sudo systemctl enable nginx
```

```bash
nano ~/auto_start.sh
```

```bash
#!/bin/bash

SESSION="demo"

# 1. Kill old session if it exists
tmux kill-session -t $SESSION 2>/dev/null

# 2. Create new session (Pane 0)
tmux new-session -d -s $SESSION

# --- PANE 0: vLLM (Port 8000) ---
# Force bash shell first so 'source' works
tmux send-keys -t $SESSION:0 "bash" C-m
sleep 1
tmux send-keys -t $SESSION:0 "source ~/anaconda3/etc/profile.d/conda.sh" C-m
tmux send-keys -t $SESSION:0 "conda activate medgemma" C-m
# Run vLLM (Port 8000)
tmux send-keys -t $SESSION:0 "vllm serve google/medgemma-1.5-4b-it --trust-remote-code --dtype bfloat16 --max-model-len 4096 --host 127.0.0.1 --port 8000 --gpu-memory-utilization 0.6" C-m

# --- PANE 1: Vision Model (Port 9000) ---
tmux split-window -v -t $SESSION:0
# Force bash shell first
tmux send-keys -t $SESSION:0.1 "bash" C-m
sleep 1
tmux send-keys -t $SESSION:0.1 "source ~/anaconda3/etc/profile.d/conda.sh" C-m
tmux send-keys -t $SESSION:0.1 "conda activate medgemma" C-m
# Run Python (Port 9000)
tmux send-keys -t $SESSION:0.1 "python medsiglip_server.py" C-m
```

```bash
chmod +x ~/auto_start.sh
```

```bash
crontab -e
```

```bash
@reboot /bin/bash /home/ubuntu/auto_start.sh
```