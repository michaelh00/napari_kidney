# napari_kidney

A napari plugin for automated spot detection in fluorescence microscopy images, powered by [Spotiflow](https://github.com/weigertlab/spotiflow).

## What it does

- Detects fluorescent spots (dots) in single images or batch-processes entire folders
- Displays detected spots as an overlay in the napari viewer
- Exports spot counts to Excel for downstream analysis

## Installation

### Prerequisites

- [Anaconda](https://www.anaconda.com/download) or Miniconda
- Git

### Step 1 — Create a conda environment

```bash
conda create -n napari_kidney python=3.11 -y
conda activate napari_kidney
```

### Step 2 — Install PyTorch

**Without GPU (CPU only):**

```bash
conda install pytorch torchvision torchaudio cpuonly -c pytorch -y
```

**With NVIDIA GPU:**

```bash
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia -y
```

### Step 3 — Install napari

```bash
pip install "napari[all]"
```

### Step 4 — Install Spotiflow and its dependencies

```bash
pip install spotiflow --no-deps
pip install scipy scikit-image tqdm h5py csbdeep aiohttp fsspec dask psutil pydash configargparse wandb tensorboard zarr "sympy==1.13.1"
pip install lightning pytorch-lightning --no-deps
pip install lightning-utilities torchmetrics
```

### Step 5 — Install the plugin

```bash
pip install git+https://github.com/yourname/napari-kidney.git
```

### Step 6 — Launch napari

```bash
napari
```

The plugin will appear under **Plugins → napari-kidney** in the napari menu.

## Usage

**Single image mode:** select a folder, pick an image from the dropdown, and click _Detect dots_. The image and detected spots will appear as layers in the napari viewer, and the dot count will be displayed.

**Batch mode:** add one or more folders, select an output Excel file path, and click _Run batch + export Excel_. All images in the selected folders will be processed and results saved to the Excel file.

## Notes

- The first run will download the Spotiflow pretrained model automatically (requires internet connection)
- The default model is `general`; other Spotiflow models can be entered in the model name field
- CPU processing is slower but works on any machine; GPU processing is significantly faster
