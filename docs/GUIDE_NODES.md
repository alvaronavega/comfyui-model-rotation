# 🎯 Guia Prático dos 8 Nós — ComfyUI Model Rotation

> Versão: 2.0.0 | Autor: Alvaro Navega | Baseado em: trunksn1

---

## ⭐ OS DOIS QUE VOCÊ USA 90% DO TEMPO

### 🔄✨ Checkpoint Rotation (Batch) — PRINCIPAL
**Quando usar:** Quer gerar muitas imagens trocando o modelo automaticamente? Conecte no `Batch Index Counter`, defina `change_interval: 5` (troca a cada 5 imagens) e rode.

**Widgets principais:**
- `model_folder`: `checkpoints` | `diffusion_models` | `unet`
- `subfolder`: caminho relativo (ex: `sdxl/`)
- `change_interval`: quantas imagens antes de trocar
- `batch_index`: **deve vir do `Batch Index Counter`**
- `rotation_mode`: `sequential` | `random` | `shuffle`
- `seed`: para random/shuffle
- `checkpoint_filter`: filtro opcional (substring)

---

### 📁 Save Image (Metadata & Export) — OBRIGATÓRIO
**Quando usar:** Sempre que usar o Rotation. Salva PNG + cria `.txt` / `.json` ao lado com nome do modelo, hash, seed, parâmetros. **Sem isso, você perde a rastreabilidade.**

---

## 🔧 AUXILIARES (conectam no principal)

### #️⃣ Batch Index Counter
Gera `0, 1, 2, 3...` a cada imagem. **Obrigatório** para o Rotation saber quando trocar.

### 🔢 Simple Counter
Contador simples (sem foco em batch). Útil para workflows simples.

---

## 🔄 OUTROS NÓS DE ROTAÇÃO

### ⚡ Checkpoint Rotation Loader (Advanced)
Versão "legacy". Mantém cache interno. **Não use** a menos que tenha workflow antigo.

### 🔀 Simple Checkpoint Rotation
Troca de modelo **sem** contador de batch. Você passa o índice manual.

### 🐞 Checkpoint Rotation (Debug)
Não carrega o modelo — só retorna o nome da seleção. Para debug: "qual modelo seria escolhido?"

---

## ✏️ UTILITÁRIO

### ✏️ Checkpoint to Filename
Pega `checkpoint_name` (saída do Rotation) e injeta no nome do arquivo salvo. Ex: `image_001_sdxl-base.png` → `...model-sdxl-base.safetensors.png`.

---

## 🧩 FLUXO TÍPICO RECOMENDADO

```
#️⃣ Batch Index Counter
    │ batch_index
    ▼
🔄✨ Checkpoint Rotation (Batch)  ◄── model_folder: "checkpoints" (ou diffusion_models/unet)
    │ model, clip, vae, checkpoint_name, info
    ├──────────────────► CLIPTextEncode (positive)
    ├──────────────────► CLIPTextEncode (negative)
    ├──────────────────► KSampler (model, clip, vae)
    │
    ▼
📁 Save Image (Metadata & Export)
    │ (recebe checkpoint_name)
    ▼
PNG + .txt + .json
```

---

## 💡 RESUMO RÁPIDO

| Seu caso | Nó(s) a usar |
|---|---|
| Geração com rotação de modelos | 🔄✨ + #️⃣ + 📁 |
| Só testar/carregar modelo | 🐞 (Debug) |
| Workflow antigo | ⚡ (Advanced) |
| Nome do modelo no arquivo | ✏️ Checkpoint to Filename |
| Não usa batch, controle manual | 🔀 Simple + 🔢 Simple Counter |
