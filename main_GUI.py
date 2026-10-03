import flet as ft
import csv
from inputprograms.rocket_simulation import RocketSimulation
from inputprograms.interp_density import OxidizerDatabase
import re
from datetime import datetime

# 現在最新バージョンへの対応作業中
# 動かす際は，旧バージョンのfletを使用するように 

# 物性値のMaster
# ABSのa,nは雑
materials_mas = [
    {"name": "MMA", "rho": 1190, "a": 0.000131, "n": 0.34},
    {"name": "ABS", "rho": 1040, "a": 0.90, "n": 1.1}
]

def main(page: ft.Page):
    page.title = "Rocket Simulation GUI"
    page.scroll = ft.ScrollMode.AUTO

    # メインビュー（初期条件＋収束）
    def main_view():
        inputs = {
            "F_req": ft.TextField(label="要求推力 [N]", width=150, value=650),
            "Pc_def": ft.TextField(label="初期燃焼室圧力 [MPa]", width=150, value=2),
            "OF_def": ft.TextField(label="初期O/F比", width=150, value=6.5),
            "mdot_new": ft.TextField(label="初期流量 [kg/s]", width=150, value=0.33),
            "Df_init": ft.TextField(label="初期燃料内径 [m]", width=150, value=0.034),
            "eta_cstar": ft.TextField(label="C*効率", width=150, value=0.8),
            "eta_nozzle": ft.TextField(label="ノズル効率", width=150, value=0.98),
        }

        result_text = ft.Text()
        graph_image = ft.Image(src = "", visible=False, width=page.width - 200)

        # 物性値の参照
        materials = materials_mas

        # Dropdown の options
        def on_material_change():
            options = []
            for material in materials:
                options.append(
                    ft.DropdownOption(
                        key = material["name"],
                        content = ft.Text(value = material["name"]),
                    )
            )
            return options

        # 表示用テキスト群
        density_text = ft.Text()
        a_text = ft.Text()
        n_text = ft.Text()

        def rho_select(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value= f"a: {selected_properties['a']}"
            n_text.value= f"n: {selected_properties['n']}"
        
        def rho_change(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value= f"a: {selected_properties['a']}"
            n_text.value= f"n: {selected_properties['n']}"
        # Dropdown 本体
        material_dropdown = ft.Dropdown(
            key = "material select",
            options = on_material_change(),
            width=250,
            on_select = rho_select,
            on_text_change = rho_change,
        )

        property_column = ft.Column(controls=[density_text, a_text, n_text], spacing=5)

        # 酸化剤補完データベース
        ox_db = OxidizerDatabase()

        pressure_input = ft.TextField(label="初期酸化剤圧力 [MPa]", width=150)
        density_output = ft.Text(value="酸化剤密度: -", size=16)

        def on_pressure_change(e):
            try:
                p = float(pressure_input.value)
                phase, rho = ox_db.get_density(p, phase = "liquid")
                result = f"{phase}密度: {rho:.2f} kg/m³"
                density_output.value = result
            except ValueError:
                density_output.value = "⚠️ 数値で入力してください"
            page.update()

        pressure_input.on_change = on_pressure_change # 挙動変更の可能性あり

        def run_simulation(e):
            try:
                # --- TextField から数値を取得 ---
                F_req      = float(inputs["F_req"].value)
                Pc_def     = float(inputs["Pc_def"].value)
                OF_def     = float(inputs["OF_def"].value)
                mdot_new   = float(inputs["mdot_new"].value)
                Df_init    = float(inputs["Df_init"].value)
                eta_cstar  = float(inputs["eta_cstar"].value)
                eta_nozzle = float(inputs["eta_nozzle"].value)

                # --- 酸化剤密度（density_output のテキストから抽出） ---
                rho_ox_init = float(
                    density_output.value.split(":")[-1].replace("kg/m³", "").strip()
                )

                # --- タンク初期圧力 ---
                Ptank_init = float(pressure_input.value)

                # --- Dropdown から材料名を取得 ---
                fuel_material = material_dropdown.value   # "MMA" or "ABS"

                # --- 材料データを取得 ---
                for m in materials:
                    if m["name"] == fuel_material:
                        props = m
                rho_f_start = float(props["rho"])
                a_ox        = float(props["a"])
                n_ox        = float(props["n"])

            except Exception as ex:
                result_text.value = f"⚠️ 入力エラー: {ex}"
                page.update()
                return

            print("input definition done. start calculation")

            sim = RocketSimulation()
            output, Dovalue, cdvalue = sim.initial_convergence(
                F_req,
                Pc_def,
                OF_def,
                mdot_new,
                Df_init,
                eta_cstar,
                eta_nozzle,
                Ptank_init,
                rho_ox_init,
                rho_f_start,
                a_ox,
                n_ox,
                fuel_material
            )
            # --- 結果表示 ---
            result_text.value = output

            graph_image.src = sim.get_iteration_plot_base64(Dovalue, cdvalue)
            graph_image.visible = True

            page.session.store.set("Pc_def", Pc_def)
            page.session.store.set("Df_init", Df_init)
            page.session.store.set("eta_cstar", eta_cstar)
            page.session.store.set("eta_nozzle", eta_nozzle)
            page.session.store.set("OF_def", OF_def)
            page.session.store.set("Ptank_init", Ptank_init)
            page.session.store.set("rho_ox_init", rho_ox_init)
            page.session.store.set("fuel_material", fuel_material)

            # resultデータのパーサー
            def parse_initial_results(text: str) -> dict:
                result = {}
                # K*
                match_k = re.search(r"K\* *= *([\d\.Ee+-]+)", text)
                if match_k:
                    result["Kstar"] = float(match_k.group(1))
                # epsilon
                match_eps = re.search(r"最終epsilon *= *([\d\.Ee+-]+)", text)
                if match_eps:
                    result["epsilon"] = float(match_eps.group(1))
                # Lf（燃料長さ）
                match_lf = re.search(r"燃料長さ *= *([\d\.Ee+-]+)", text)
                if match_lf:
                    result["Lf"] = float(match_lf.group(1))
                # mdot
                match_mdot = re.search(r"最終mdot *= *([\d\.Ee+-]+)", text)
                if match_mdot:
                    result["mdot"] = float(match_mdot.group(1))
                # 初期推力F
                match_F = re.search(r"最終推力 *= *([\d\.Ee+-]+)", text)
                if match_F:
                    result["F"] = float(match_F.group(1))
                # Dt
                match_Dt = re.search(r"計算結果Dt *= *([\d\.Ee+-]+)", text)
                if match_Dt:
                    result["Dt"] = float(match_Dt.group(1))

                return result

            results_parsed = parse_initial_results(output)

            page.session.store.set("Kstar", results_parsed["Kstar"])
            page.session.store.set("epsilon", results_parsed["epsilon"])
            page.session.store.set("Lf", results_parsed["Lf"])
            page.session.store.set("mdot", results_parsed["mdot"])
            page.session.store.set("F", results_parsed["F"])
            page.session.store.set("Dt", results_parsed["Dt"])
            
            page.update()

        # 実行ボタンと遷移ボタンを並べる

        def goto_evolution(e):
            page.route = "/evolution"
            page.on_route_change = route_change()
            page.update()

        action_row = ft.Row(
            [
                ft.Button("収束計算", on_click=run_simulation),
                ft.Button("▶ 時間発展ページへ", on_click=goto_evolution)
            ]
        )

        # 左側：入力群＋結果＋ボタン群＋ログ
        input_column = ft.Column(
            controls=[*list(inputs.values()),
                    pressure_input,
                    density_output,
                    material_dropdown,
                    property_column,
                    action_row, 
                    result_text],
            spacing=10,
            expand=True,
            height=page.height + 100,
            scroll=ft.ScrollMode.AUTO,
        )

        # 右側：収束グラフと K* グラフを縦に並べる
        graph_image = ft.Image(src = "", visible=False, width=page.width - 200)

        graph_column = ft.Column(
            controls=[graph_image],
            spacing=10,
            expand=True,
            height=page.height + 100,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )

        return ft.View(
            route="/",
            controls=[
                ft.Row(
                    controls=[input_column, graph_column],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            ],
        )

    # 時間発展ビュー（別ページ）
    def evolution_view():
        results_graph_image = ft.Image(src= "", visible=False, width=600)

        # 初期値がある場合は値を埋める、なければ空欄
        Pc_def = str(page.session.store.get("Pc_def")) 
        Df_init = str(page.session.store.get("Df_init")) 
        eta_cstar = str(page.session.store.get("eta_cstar")) 
        eta_nozzle = str(page.session.store.get("eta_nozzle")) 
        OF_def = str(page.session.store.get("OF_def")) 
        Pt_init = str(page.session.store.get("Ptank_init")) 
        rho_ox = str(page.session.store.get("rho_ox_init")) 
        fuel_material = str(page.session.store.get("fuel_material")) 

        Kstar = str(page.session.store.get("Kstar")) 
        epsilon = str(page.session.store.get("epsilon")) 
        Lf = str(page.session.store.get("Lf")) 
        mdot = str(page.session.store.get("mdot")) 
        F = str(page.session.store.get("F")) 
        Dt = str(page.session.store.get("Dt")) 

        # 入力欄の定義
        Pc_box = ft.TextField(label="燃焼室圧力 Pc [MPa]", value=Pc_def, width=150)
        Df_box = ft.TextField(label="初期ポート径 Df [m]", value=Df_init, width=150)
        OF_box = ft.TextField(label="初期OF比", value=OF_def, width=150)
        eta_cstar_box = ft.TextField(label="C*効率", value=eta_cstar, width=150)
        eta_nozzle_box = ft.TextField(label="ノズル効率", value=eta_nozzle, width=150)

        # 物性値の参照
        materials = materials_mas

        # Dropdown の options
        def on_material_change():
            options = []
            for material in materials:
                options.append(
                    ft.DropdownOption(
                        key = material["name"],
                        content = ft.Text(value = material["name"]),
                    )
            )
            return options

        # 表示用テキスト群
        density_text = ft.Text()
        a_text = ft.Text()
        n_text = ft.Text()

        def rho_select(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value= f"a: {selected_properties['a']}"
            n_text.value= f"n: {selected_properties['n']}"
        
        def rho_change(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value= f"a: {selected_properties['a']}"
            n_text.value= f"n: {selected_properties['n']}"
        # Dropdown 本体
        material_dropdown = ft.Dropdown(
            key = "material select",
            options = on_material_change(),
            value = fuel_material,
            width=150,
            on_select = rho_select,
            on_text_change = rho_change,
        )

        property_column = ft.Column(controls=[density_text, a_text, n_text], spacing=5)

        Kstar_box = ft.TextField(label="K*", value=Kstar, width=150)
        epsilon_box = ft.TextField(label="膨張比 ε", value=epsilon, width=150)
        Lf_box = ft.TextField(label="燃焼長 Lf [m]", value=Lf, width=150)
        mdot_box = ft.TextField(label="推進剤流量 mdot [kg/s]", value=mdot, width=150)
        F_box = ft.TextField(label="初期推力F [N]", value=F, width=150)
        Dt_box = ft.TextField(label="スロート径 [m]", value=Dt, width=150)

        # タンク容積と最終酸化剤圧力の入力欄
        tank_volume_input = ft.TextField(label="タンク容積 [m³]", width=150)
        initial_pressure_input = ft.TextField(label="初期酸化剤圧力 [MPa]", value=Pt_init,width=150)
        rho_ox_input = ft.TextField(label="初期酸化剤密度(圧力をいじる場合は調整してください．) [kg/s]", value=rho_ox,width=150)
        final_pressure_input = ft.TextField(label="最終酸化剤圧力 [MPa]", width=150)
        cea_input = ft.TextField(label="CEA更新頻度", width=150)

        csv_download_button = ft.Button(
            "CSV出力 ⬇",
            icon=ft.Icons.DOWNLOAD,
            visible=False,
            on_click=lambda _: None,
        )

        def get_csv_download_link(input_params, performance_params, evolution_result):
            print("output")

            # ヘッダー行（evolution_resultの列順に対応）
            evolution_headers = [
                "F [N]",
                "F_fte [N]",
                "Ptank [MPa]",
                "Pc [MPa]",
                "O/F [-]",
                "mdot [kg/s]",
                "Df [m]",
                "C* [m/s]",
                "CF [-]",
                "tank mass [g]",
                "mdot_ox [g/ms]",
                "gamma [-]"
            ]

            # 現在時刻をファイル名に付与
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"result_{timestamp}.csv"

            # csv保存
            with open(filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file, quoting=csv.QUOTE_NONE)
                # 入力パラメータの書き出し
                writer.writerow(["# input params."])
                for i in range(0, len(input_params), 3):
                    row = []
                    for j in range(3):
                        if i + j < len(input_params):
                            key, val = input_params[i + j]
                            row.extend([key, val])
                    writer.writerow(row)


                writer.writerow([])  # 空行
                writer.writerow(["# performance params."])
                for i in range(0, len(performance_params), 3):
                    row = []
                    for j in range(3):
                        if i + j < len(performance_params):
                            key, val = performance_params[i + j]
                            row.extend([key, val])
                    writer.writerow(row)

                writer.writerow([])  # 空行

                writer.writerow(["# evolution params."])
                writer.writerow(evolution_headers)
                writer.writerows(evolution_result)


        # 関数に放り込む部分
        sim = RocketSimulation()

        def on_run_simulation(e):
            try:
                # 各入力欄から値を取得
                Pc = float(Pc_box.value)
                Df = float(Df_box.value)
                OF = float(OF_box.value)
                eta_cstar = float(eta_cstar_box.value)
                eta_nozzle = float(eta_nozzle_box.value)
                Kstar = float(Kstar_box.value)
                epsilon = float(epsilon_box.value)
                Lf = float(Lf_box.value)
                mdot = float(mdot_box.value)
                V_tank = float(tank_volume_input.value)
                P_init = float(initial_pressure_input.value)
                P_final = float(final_pressure_input.value)
                F_init = float(F_box.value)
                Dt = float(Dt_box.value)
                rho_ox = float(rho_ox_input.value)
                fuel_material = material_dropdown.value
                for m in materials:
                    if m["name"] == fuel_material:
                        props = m
                rho_f = float(props["rho"])
                a_ox  = float(props["a"])
                n_ox  = float(props["n"])
                cea_interval = float(cea_input.value)

            except Exception as ex:
                evolution_output.value = f"⚠️ 入力エラー: {ex}"
                page.update()
                return


            try:
                # RocketSimulation呼び出し
                (
                    time_ms,
                    F_arr,
                    F_fte_arr,
                    OF_arr,
                    Cstar_arr,
                    Pc_arr,
                    Pt_arr,
                    evolution_result,
                    It,
                    tb,
                    Isp
                ) = sim.integration_simulation(
                    Pc=Pc,
                    Df=Df,
                    OF=OF,
                    eta_cstar=eta_cstar,
                    eta_nozzle=eta_nozzle,
                    Kstar=Kstar,
                    epsilon=epsilon,
                    Lf=Lf,
                    mdot=mdot,
                    V_tank=V_tank,
                    P_init=P_init,
                    P_final=P_final,
                    rho_ox=rho_ox,
                    rho_fuel=rho_f,
                    a=a_ox,
                    n=n_ox,
                    fuel_material=fuel_material,
                    F=F_init,
                    Dt=Dt,
                    cea_interval=cea_interval
                )

                # 結果表示（仮）
                evolution_output.value = f"✅ 計算完了, Total Inpulse = {It}[Ns], 燃焼時間{tb}[sec], Isp{Isp}[s]"
            except Exception as ex:
                evolution_output.value = f"⚠️ 計算エラー: {ex}"
                print(ex)
            
            input_params = [
                ("Pc", Pc), ("Df", Df), ("OF", OF),
                ("eta_cstar", eta_cstar), ("eta_nozzle", eta_nozzle), ("Kstar", Kstar),
                ("epsilon", epsilon), ("Lf", Lf), ("mdot", mdot),
                ("V_tank", V_tank), ("P_init", P_init), ("P_final", P_final),
                ("rho_ox", rho_ox), ("rho_fuel", rho_f),
                ("a", a_ox), ("n", n_ox), ("F", F_init), ("Dt", Dt),
                ("Fuel Material",fuel_material)
            ]

            performance_params = [
                ("It", It), ("Tb", tb), ("Isp", Isp) 
            ]
            def on_csv_download_click(e):
                csv_data_url = get_csv_download_link(input_params, performance_params, evolution_result)

            csv_download_button.on_click = on_csv_download_click
            csv_download_button.visible = True
            results_graph_image.src = sim.get_evolution_plot_base64(
                time_ms, F_arr, F_fte_arr, OF_arr, Cstar_arr, Pc_arr, Pt_arr
            )
            results_graph_image.visible = True
            page.update()

        run_button = ft.Button(
            "時間発展計算 ▶", on_click=on_run_simulation
        )
        evolution_output = ft.Text("🕒 時間発展シミュレーション")

        def go_back(e):
                    page.route = "/"
                    page.on_route_change = route_change()
                    page.update()

        return ft.View(
            route="/evolution",
            controls=[
                ft.Text("時間発展ページ", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        # 1列目
                        ft.Column(
                            [
                                ft.Text("初期状態パラメータ①："),
                                Pc_box,
                                Df_box,
                                OF_box,
                                eta_cstar_box,
                                eta_nozzle_box,
                                material_dropdown,
                                property_column,
                            ],
                            spacing=10,
                        ),
                        # 2列目
                        ft.Column(
                            [
                                ft.Text("初期状態パラメータ②："),
                                Kstar_box,
                                epsilon_box,
                                Lf_box,
                                mdot_box,
                                F_box,
                            ],
                            spacing=10,
                        ),
                        # 3列目
                        ft.Column(
                            [
                                ft.Text("初期状態パラメータ③："),
                                Dt_box,
                                tank_volume_input,
                                initial_pressure_input,
                                rho_ox_input, 
                                final_pressure_input,
                                cea_input,
                            ],
                            spacing=10,
                        ),
                        # ✅ 4列目：グラフ表示
                        ft.Column(
                            [ft.Text("時間発展グラフ："), results_graph_image],
                            spacing=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Row(
                    controls=[run_button, csv_download_button, evolution_output],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.TextButton("◀ 戻る", on_click=go_back),
            ],
        )
    
    # ページ切り替え処理
    def route_change():
        page.views.clear()
        if page.route == "/":
            page.views.append(main_view())
        elif page.route == "/evolution":
            page.views.append(evolution_view())
        page.update()

    page.on_route_change = route_change()
    page.route = "/"
    page.update()


ft.run(main)
