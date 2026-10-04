# FTE enginesimulator 2.0.0. GUI
大本の，CLIから派生してGUIサポート専用のリポジトリです．

CLIのバージョン更新を反映してこちらを更新していく予定．

現在のCLIバージョン：v2.0.0 + 2commit
(https://github.com/Kazuki-723/fte-enginesimulation/commit/f4ff21805846a1168da967d810ac82a33882d3bb)

ここから先はCLIのコピーなので後ほど修正．

# 環境構築

基本的にuvで管理している，

現在は
```
Python 3.14.x
├── cea v3.3.4
├── flet v1.0.3
├── flet-desktop v1.0.3
├── matplotlib v3.11.2
├── numpy v2.5.3
├── pandas v3.0.6
├── scipy v1.18.1
└── tqdm v4.70.1
```

として管理している．(各ライブラリのさらなる依存は省略)

uvを用意したうえで(`uv sync`)をコマンドで打てば勝手に.venvから環境を構築してくれるはずである，



動作には，このgithub以外に，NISTから持ってきたN2Oの気液平衡曲線の密度データ表が必要になる．適宜自分で用意するかほかの人からもらうようにしてほしい．

# NASACEA license 
Modifications:

   Custom 4 species data added by FROM THE EARTH Tohoku University Student Rocket team, 2026.
   Original NASA CEA code is Apache License 2.0.