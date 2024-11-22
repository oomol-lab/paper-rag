# parpers-rag

# 安装

## conda 环境

需要 Python 环境，执行如下命令创建 Python 的 `venv` 环境。

```shell
$ conda create --prefix ./.venv python=3.12.7 -y
```

此后切换到该 Python 环境。对于 Linux / MacOS 而言执行如下命令。

```shell
$ conda activate ./.venv
```

此后安装依赖包，执行如下命令。

```shell
$ pip install --upgrade pip
$ pip install -r requirements.txt
```

退出环境
```shell
$ conda deactivate
```

## Spacy 模型

其中 Spacy 依赖的中英文模型，通过如下命令安装。

```shell
$ python -m spacy download en_core_web_sm
$ python -m spacy download zh_core_web_sm
```

# 发布 Windows 版

## 在 MacOS 上的准备

执行如下命令，构造供 windows 进一步构建的的压缩包。

```shell
./build/build-win.sh
```

找到 `dist/PaperRAG-win-amd64.zip` 文件，将它复制到 Windows 设备上并解压缩。

## 在 Windows 上的构建

解压缩压缩包，并确保设备已安装 Anaconda。在解压缩后的项目中用 CMD 执行如下命令。

```bat
conda create --prefix ./.paper-rag-venv python=3.12.7 -y
```

打开 Anaconda 的图形界面，找到 `.paper-rag-venv` 然后点播放键打开，再依次执行如下命令。

```bat
cd XXXXX # 文件夹根目录
.\.paper-rag-venv\python.exe -m pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
```

## 在 Windows 上运行

双击 `start.bat` 文件即可。