import flet as ft
import csv
from inputprograms.rocket_simulation_levelset import RocketSimulation_levelset
from inputprograms.rocket_simulation import RocketSimulation
from inputprograms.interp_density import OxidizerDatabase
from inputprograms.iteration_logger import IterationLogger
import inputprograms.make_sample_geometry
import re
from datetime import datetime
import base64
import numpy as np
from io import StringIO
from inputprograms.fuel_geometry import FuelGeometry

# クラス定義
sim_lev   = RocketSimulation_levelset()
sim       = RocketSimulation()
ox_db     = OxidizerDatabase()
geom_make = inputprograms.make_sample_geometry
geom_calc = FuelGeometry()

# 物性値のMaster
# ABSのa,nは雑
materials_mas = [
    {"name": "MMA", "rho": 1190, "a": 0.000131, "n": 0.34},
    {"name": "ABS", "rho": 1040, "a": 0.90, "n": 1.1}
]

def main(page: ft.Page):
    page.title = "Rocket Simulation GUI"
    page.scroll = ft.ScrollMode.AUTO

    page.horizontal_alignment = ft.CrossAxisAlignment.START
    page.vertical_alignment = ft.MainAxisAlignment.START

    # ============================
    # 共通ページ遷移関数
    # ============================
    # 初期の形状選択画面
    def goto_shape_select(e):
        page.route = "/shape_select"
        page.on_route_change = route_change()
        page.update()

    # 円形ポート計算用の初期画面
    def goto_main(e):
        page.route = "/main"
        page.on_route_change = route_change()
        page.update()

    # 円形ポート計算用の時間発展画面
    def goto_evolution(e):
        page.route = "/evolution"
        page.on_route_change = route_change()
        page.update()

    # geometry点群計算用の初期画面
    def goto_noncircular(e):
        page.route = "/noncircular"
        page.on_route_change = route_change()
        page.update()

    # levelset関数計算画面
    def goto_levelset_calc(e):
        page.route = "/levelset_calc"
        page.on_route_change = route_change()
        page.update()

    # levelsetによる初期条件計算
    def goto_initial_condition(e):
        page.route = "/levelset_initial_condition"
        page.on_route_change = route_change()
        page.update()
    
    # levelsetによる時間発展計算
    def goto_evo_levelset(e):
        page.route = "/levelset_evo_condition"
        page.on_route_change = route_change()
        page.update()

    # ============================
    # 共通数値バリデーション関数
    # ============================
    def validate_positive_float(value, name):
        try:
            v = float(value)
            if v <= 0:
                raise ValueError(f"{name} は 0 より大きい値を入力してください")
            return v
        except:
            raise ValueError(f"{name} は正の数値(float)で入力してください")


    def validate_positive_int(value, name):
        try:
            v = int(value)
            if v <= 0:
                raise ValueError(f"{name} は 0 より大きい整数(int)を入力してください")
            return v
        except:
            raise ValueError(f"{name} は正の整数(int)で入力してください")

    # ============================
    # データパース関数
    # ============================
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

    # ============================
    # ヘッダー関数
    # ============================
    def build_header(current_route):

        # 円形ルート
        circular_steps = [
            ("形状選択", "/shape_select", goto_shape_select),
            ("円形初期設定", "/main", goto_main),
            ("円形時間発展", "/evolution", goto_evolution),
        ]

        # 非円形ルート
        noncircular_steps = [
            ("形状選択", "/shape_select", goto_shape_select),
            ("非円形geometry", "/noncircular", goto_noncircular),
            ("levelset計算", "/levelset_calc", goto_levelset_calc),
            ("初期条件計算", "/levelset_initial_condition", goto_initial_condition),
            ("時間発展", "/levelset_evo_condition", goto_evo_levelset),
        ]

        # ルート判定
        if current_route in ["/main", "/evolution"]:
            steps = circular_steps
        else:
            steps = noncircular_steps

        # ステップバーの各要素を作成
        step_controls = []
        for label, route, func in steps:

            # 状態判定
            if current_route == route:
                # 現在のステップ
                icon = ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED, color="#4A90E2")
                text_color = "#64B5F6"
            else:
                # 未完了ステップ
                icon = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, color="#CCCCCC")
                text_color = "#CCCCCC"

            step_controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            icon,
                            ft.Text(label, color=text_color, size=16),
                        ],
                        spacing=5,
                    ),
                    padding=10,
                    on_click=func,
                )
            )

        # 一番右の「形状選択に戻る」
        step_controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.RESTART_ALT, color="#FF8888"),
                        ft.Text("最初に戻る", color="#FF8888", size=16),
                    ],
                    spacing=5,
                ),
                padding=10,
                on_click=goto_shape_select,
            )
        )

        # ステップバー本体
        return ft.Container(
            content=ft.Row(
                controls=step_controls,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="#1E1E1E",
            padding=10,
        )

    # 形状選択ビュー
    def shape_select_view():
        return ft.View(
            route="/shape_select",
            controls=[
                ft.Column(
                    [
                        ft.Text("ポート形状を選択してください", size=24, weight="bold"),

                        ft.Row(
                            [
                                ft.Button(
                                    "円形ポート",
                                    on_click=goto_main,
                                    bgcolor="#415FA0",
                                    color="#C0CAF5",
                                    style=ft.ButtonStyle(
                                        overlay_color="#2D3F64",
                                        shadow_color="#000000",
                                    ),
                                ),
                                ft.Button(
                                    "円形以外のポート",
                                    on_click=goto_noncircular,
                                    bgcolor="#415FA0",
                                    color="#C0CAF5",
                                    style=ft.ButtonStyle(
                                        overlay_color="#2D3F64",
                                        shadow_color="#000000",
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                )
            ]
        )


    # 円形ポートmainview
    def main_view():
        inputs = {
            "F_req": ft.TextField(label="要求推力 [N]", width=150, value=650),
            "Pc_def": ft.TextField(label="初期燃焼室圧力 [MPa]", width=150, value=2),
            "OF_def": ft.TextField(label="初期O/F比", width=150, value=6.5),
            "mdot_new": ft.TextField(label="初期流量 [kg/s]", width=150, value=0.33),
            "Df_init": ft.TextField(label="初期燃料内径 [m]", width=150, value=0.034),
            "eta_cstar": ft.TextField(label="C*効率", width=150, value=0.8),
            "eta_nozzle": ft.TextField(label="ノズル効率", width=150, value=1),
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
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        
        def rho_change(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        # Dropdown 本体
        material_dropdown = ft.Dropdown(
            key = "material select",
            options = on_material_change(),
            width=250,
            on_select = rho_select,
            on_text_change = rho_change,
        )

        property_column = ft.Column(controls=[density_text, a_text, n_text], spacing=5)

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

            # グラフ画像の取得
            graph_image.src = sim.get_iteration_plot_base64(Dovalue, cdvalue)
            graph_image.visible = True

            # 画像の保存
            # base64 → バイナリに変換
            image_bytes = base64.b64decode(graph_image.src)

            # 保存先（相対パス）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imageoutput\\init_result_graph_{timestamp}.png"

            # PNG として保存
            with open(filename, "wb") as f:
                f.write(image_bytes)

            page.session.store.set("Pc_def", Pc_def)
            page.session.store.set("Df_init", Df_init)
            page.session.store.set("eta_cstar", eta_cstar)
            page.session.store.set("eta_nozzle", eta_nozzle)
            page.session.store.set("OF_def", OF_def)
            page.session.store.set("Ptank_init", Ptank_init)
            page.session.store.set("rho_ox_init", rho_ox_init)
            page.session.store.set("fuel_material", fuel_material)

            results_parsed = parse_initial_results(output)

            page.session.store.set("Kstar", results_parsed["Kstar"])
            page.session.store.set("epsilon", results_parsed["epsilon"])
            page.session.store.set("Lf", results_parsed["Lf"])
            page.session.store.set("mdot", results_parsed["mdot"])
            page.session.store.set("F", results_parsed["F"])
            page.session.store.set("Dt", results_parsed["Dt"])
            
            page.update()

        # 実行ボタンと遷移ボタンを並べる

        action_row = ft.Row(
            [
                ft.Button(
                    "収束計算", 
                    on_click=run_simulation,
                    bgcolor="#415FA0",
                    color="#C0CAF5",
                    style=ft.ButtonStyle(
                        overlay_color="#2D3F64",
                        shadow_color="#000000",
                    ),
                ),
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
        graph_column = ft.Column(
            controls=[graph_image],
            spacing=10,
            expand=True,
            height=page.height + 100,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )

        return ft.View(
            route="/main",
            controls=[
                build_header("/main"),
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
        Pc_def        = str(page.session.store.get("Pc_def")) 
        Df_init       = str(page.session.store.get("Df_init")) 
        eta_cstar     = str(page.session.store.get("eta_cstar")) 
        eta_nozzle    = str(page.session.store.get("eta_nozzle")) 
        OF_def        = str(page.session.store.get("OF_def")) 
        Pt_init       = str(page.session.store.get("Ptank_init")) 
        rho_ox        = str(page.session.store.get("rho_ox_init")) 
        fuel_material = str(page.session.store.get("fuel_material")) 

        Kstar   = str(page.session.store.get("Kstar")) 
        epsilon = str(page.session.store.get("epsilon")) 
        Lf      = str(page.session.store.get("Lf")) 
        mdot    = str(page.session.store.get("mdot")) 
        F       = str(page.session.store.get("F")) 
        Dt      = str(page.session.store.get("Dt")) 

        # 入力欄の定義
        Pc_box         = ft.TextField(label="燃焼室圧力 Pc [MPa]", value=Pc_def, width=150)
        Df_box         = ft.TextField(label="初期ポート径 Df [m]", value=Df_init, width=150)
        OF_box         = ft.TextField(label="初期OF比", value=OF_def, width=150)
        eta_cstar_box  = ft.TextField(label="C*効率", value=eta_cstar, width=150)
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
        a_text       = ft.Text()
        n_text       = ft.Text()

        def rho_select(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        
        def rho_change(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        # Dropdown 本体
        material_dropdown = ft.Dropdown(
            key = "material select",
            options = on_material_change(),
            value = fuel_material,
            width = 150,
            on_select = rho_select,
            on_text_change = rho_change,
        )

        property_column = ft.Column(controls=[density_text, a_text, n_text], spacing=5)

        Kstar_box   = ft.TextField(label="K*", value=Kstar, width=150)
        epsilon_box = ft.TextField(label="膨張比 ε", value=epsilon, width=150)
        Lf_box      = ft.TextField(label="燃焼長 Lf [m]", value=Lf, width=150)
        mdot_box    = ft.TextField(label="推進剤流量 mdot [kg/s]", value=mdot, width=150)
        F_box       = ft.TextField(label="初期推力F [N]", value=F, width=150)
        Dt_box      = ft.TextField(label="スロート径 [m]", value=Dt, width=150)

        # タンク容積と最終酸化剤圧力の入力欄
        tank_volume_input      = ft.TextField(label="タンク容積 [m³]", width=150)
        initial_pressure_input = ft.TextField(label="初期酸化剤圧力 [MPa]", value=Pt_init,width=150)
        rho_ox_input           = ft.TextField(label="初期酸化剤密度(圧力をいじる場合は調整してください．) [kg/s]", value=rho_ox,width=150)
        final_pressure_input   = ft.TextField(label="最終酸化剤圧力 [MPa]", width=150)
        cea_input              = ft.TextField(label="CEA更新頻度", width=150)

        csv_download_button = ft.Button(
            "CSV出力 ⬇",
            icon=ft.Icons.DOWNLOAD,
            visible=False,
            on_click=lambda _: None,
            bgcolor="#48865D",
            color="#C0CAF5",
            style=ft.ButtonStyle(
                overlay_color="#2F533B",
                shadow_color="#000000",
            ),
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
        def on_run_simulation(e):
            try:
                # 各入力欄から値を取得
                Pc            = float(Pc_box.value)
                Df            = float(Df_box.value)
                OF            = float(OF_box.value)
                eta_cstar     = float(eta_cstar_box.value)
                eta_nozzle    = float(eta_nozzle_box.value)
                Kstar         = float(Kstar_box.value)
                epsilon       = float(epsilon_box.value)
                Lf            = float(Lf_box.value)
                mdot          = float(mdot_box.value)
                V_tank        = float(tank_volume_input.value)
                P_init        = float(initial_pressure_input.value)
                P_final       = float(final_pressure_input.value)
                F_init        = float(F_box.value)
                Dt            = float(Dt_box.value)
                rho_ox        = float(rho_ox_input.value)
                fuel_material = material_dropdown.value

                for m in materials:
                    if m["name"] == fuel_material:
                        props = m
                
                rho_f        = float(props["rho"])
                a_ox         = float(props["a"])
                n_ox         = float(props["n"])
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
                    Pc            = Pc,
                    Df            = Df,
                    OF            = OF,
                    eta_cstar     = eta_cstar,
                    eta_nozzle    = eta_nozzle,
                    Kstar         = Kstar,
                    epsilon       = epsilon,
                    Lf            = Lf,
                    mdot          = mdot,
                    V_tank        = V_tank,
                    P_init        = P_init,
                    P_final       = P_final,
                    rho_ox        = rho_ox,
                    rho_fuel      = rho_f,
                    a             = a_ox,
                    n             = n_ox,
                    fuel_material = fuel_material,
                    F             = F_init,
                    Dt            = Dt,
                    cea_interval  = cea_interval
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

            # 結果csvのダウンロード処理
            csv_download_button.on_click = on_csv_download_click
            csv_download_button.visible = True

            # resultのグラフ描画
            results_graph_image.src = sim.get_evolution_plot_base64(
                time_ms, F_arr, F_fte_arr, OF_arr, Cstar_arr, Pc_arr, Pt_arr
            )
            results_graph_image.visible = True

            # 画像の保存
            # base64 → バイナリに変換
            image_bytes = base64.b64decode(results_graph_image.src)

            # 保存先（相対パス）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imageoutput\\evo_result_graph_{timestamp}.png"

            # PNG として保存
            with open(filename, "wb") as f:
                f.write(image_bytes)
            page.update()

        run_button = ft.Button(
            "時間発展計算 ▶", 
            on_click=on_run_simulation,
            bgcolor="#415FA0",
            color="#C0CAF5",
            style=ft.ButtonStyle(
                overlay_color="#2D3F64",
                shadow_color="#000000",
            ),
        )
        evolution_output = ft.Text("🕒 時間発展シミュレーション")

        return ft.View(
            route="/evolution",
            controls=[
                build_header("/evolution"),
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
            ],
        )

    def noncircular_geometry_view():
        # dummyのgeometryとshapeを作成
        geometry = []
        shape = None

        # 動的に切り替えるフォームを入れるコンテナ
        form_container = ft.Column(expand=True)

        # 結果のgeometry表示用
        geometry_image = ft.Image(src="", visible=False, expand=True)

        # --- 各形状のフォーム定義 ---
        # gizagiza
        gizagiza_d = ft.TextField(label="d（内径）", width=200)
        gizagiza_D = ft.TextField(label="D（外径）", width=200)
        gizagiza_n = ft.TextField(label="n（ギザ数）", width=200)

        gizagiza_form = ft.Column(
            [
                gizagiza_d,
                gizagiza_D,
                gizagiza_n,
            ]
        )

        # gear
        gear_d = ft.TextField(label="d（内径）", width=200)
        gear_D = ft.TextField(label="D（外径）", width=200)
        gear_ratio = ft.TextField(label="ratio（内径:外径）", width=200)
        gear_n = ft.TextField(label="n（ギザ数）", width=200)

        gear_form = ft.Column(
            [
                gear_d,
                gear_D,
                gear_ratio,
                gear_n,
            ]
        )

        # koch
        koch_order = ft.TextField(label="order（再帰回数）", width=200)
        koch_scale = ft.TextField(label="scale（一辺長）", width=200)

        koch_form = ft.Column(
            [
                koch_order,
                koch_scale,
            ]
        )

        geometry_csv_button = ft.Button("CSV 出力", 
                                            visible=False, 
                                            on_click=lambda _: None,
                                            bgcolor="#48865D",
                                            color="#C0CAF5",
                                            style=ft.ButtonStyle(
                                                overlay_color="#2F533B",
                                                shadow_color="#000000",
                                            ),
                                        )

        # --- Dropdown 選択時の動作 ---
        def on_shape_change(e):
            selected = e.data
            form_container.controls.clear()

            if selected == "gizagiza":
                form_container.controls.append(gizagiza_form)

            elif selected == "gear":
                form_container.controls.append(gear_form)

            elif selected == "koch":
                form_container.controls.append(koch_form)

            page.update()

        # 形状選択用 Dropdown
        shape_dropdown = ft.Dropdown(
            label="ポート形状を選択",
            options=[
                ft.dropdown.Option("gizagiza"),
                ft.dropdown.Option("gear"),
                ft.dropdown.Option("koch"),
            ],
            on_select=on_shape_change,
            on_text_change=on_shape_change,
            width=200,
        )

        # --- ここから geometry 生成処理を追加 ---
        result_text = ft.Text("")

        def generate_geometry(e):
            shape = shape_dropdown.value

            try:
                if shape == "gizagiza":
                    d = validate_positive_float(gizagiza_d.value, "d（内径）")
                    D = validate_positive_float(gizagiza_D.value, "D（外径）")
                    n = validate_positive_int(gizagiza_n.value, "n（ギザ数）")

                    if d >= D:
                        raise ValueError("内径 d は外径 D より小さい必要があります")

                    geometry = geom_make.make_gizagiza(d, D, n)

                elif shape == "gear":
                    d = validate_positive_float(gear_d.value, "d（内径）")
                    D = validate_positive_float(gear_D.value, "D（外径）")
                    ratio = validate_positive_float(gear_ratio.value, "ratio")
                    n = validate_positive_int(gear_n.value, "n（ギザ数）")

                    if d >= D:
                        raise ValueError("内径 d は外径 D より小さい必要があります")

                    geometry = geom_make.make_gear(d, D, (1, ratio), n)

                elif shape == "koch":
                    order = validate_positive_int(koch_order.value, "order（再帰回数）")
                    scale = validate_positive_float(koch_scale.value, "scale（一辺長）")

                    if order >= 10:
                        raise ValueError("再帰回数が多すぎます")

                    geometry = geom_make.koch_snowflake(order, scale)

                else:
                    result_text.value = "⚠️ 形状が選択されていません"
                    page.update()
                    return

            except ValueError as err:
                result_text.value = f"⚠️ 入力エラー: {err}"
                page.update()
                return

            # 画像処理
            geometry_image.src = IterationLogger.plot_geometry(geometry)
            geometry_image.visible = True

            # テキスト処理
            result_text.value = f"geometry を生成しました（点数: {len(geometry)}）"

            # csvdownload用の発火点
            def on_csv_download_click(e):
                csv_data_url = export_csv(shape, geometry)

            geometry_csv_button.on_click = on_csv_download_click
            geometry_csv_button.visible = True

            page.update()

        # --- CSV 出力処理 ---
        def export_csv(shape, geometry):
            if shape is None:
                result_text.value = "⚠️ 先にジオメトリを生成してください"
                page.update()
                return

            # 点データ増殖
            threshold = 1e-4
            dense_geom = geom_make.densify_geometry(geometry, threshold)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{shape}_geometry_{timestamp}.csv"

            np.savetxt(filename, dense_geom, fmt="%.6f", delimiter=",")

            result_text.value = f"CSV を出力しました: {filename}"
            page.update()
        
        # --- 画面構成 ---
        return ft.View(
            route="/noncircular",
            controls=[
                build_header("/noncircular"),
                ft.Row(
                    controls=[
                        # 左側：入力フォーム
                        ft.Column(
                                    [
                                        ft.Text("非円形ポート形状の入力", size=24, weight="bold"),
                                        shape_dropdown,
                                        form_container,
                                        ft.Row(
                                            controls=[
                                                ft.Button(
                                                        "ジオメトリ生成", 
                                                        on_click=generate_geometry,
                                                        bgcolor="#415FA0",
                                                        color="#C0CAF5",
                                                        style=ft.ButtonStyle(
                                                            overlay_color="#2D3F64",
                                                            shadow_color="#000000",
                                                        ),
                                                    ),
                                                geometry_csv_button,
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                        result_text,
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    expand=True,
                                ),

                                # 右側：画像表示
                                ft.Column(
                                    [
                                        geometry_image,
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    expand=True,
                                ),
                            ],
                            expand=True,
                        )
                    ]
                )

    def levelset_calc_view():
        selected_file_name = ft.Text("No file selected")

        # 読み込んだgeometry表示用
        loaded_geometry_image = ft.Image(src="", visible=False, expand=True)

        # levelset表示用
        levelset_image = ft.Image(src="", visible=False, expand=True)

        # --- 中央列：6つの入力フィールド ---
        Nx_field    = ft.TextField(label="x方向の分割値", width=200, value = 600)
        Ny_field    = ft.TextField(label="y方向の分割値", width=200, value = 600)
        x_min_field = ft.TextField(label="x_min", width=200, value = -0.001)
        x_max_field = ft.TextField(label="x_max", width=200, value = 0.001)
        y_min_field = ft.TextField(label="y_min", width=200, value = -0.001)
        y_max_field = ft.TextField(label="y_max", width=200, value = 0.001)
        result_text = ft.Text()

        async def pick_csv_file(_: ft.Event[ft.Button]):
                files = await ft.FilePicker().pick_files(
                    allow_multiple=False,
                    with_data=True,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["csv"],
                )
                if not files:
                    selected_file_name.value = "Selection cancelled"
                    return
        
                selected = files[0]
                selected_file_name.value = f"Selected: {selected.name} ({selected.size} bytes)"
                raw = (
                    selected.bytes.decode("utf-8", errors="replace") if selected.bytes else ""
                )
                loaded_geometry = np.loadtxt(StringIO(raw), delimiter=",")

                page.session.store.set("loaded_geometry_filename", selected.name)
                page.session.store.set("loaded_geometry", loaded_geometry)

                loaded_geometry_image.src = IterationLogger.plot_geometry(loaded_geometry)
                loaded_geometry_image.visible = True

        def run_distance_calc():
            # CSV が読み込まれているかチェック
            if page.session.store.get("loaded_geometry") is None:
                result_text.value = "⚠️ 先に CSV を読み込んでください"
                page.update()
                return

            # 必要な値を取り出す
            try:
                loaded_geometry = page.session.store.get("loaded_geometry")

                # 型チェック + 正の値チェック
                Nx = validate_positive_int(Nx_field.value, "Nx（x方向の分割数）")
                Ny = validate_positive_int(Ny_field.value, "Ny（y方向の分割数）")
                min_x = float(x_min_field.value)
                min_y = float(y_min_field.value)
                max_x = float(x_max_field.value)
                max_y = float(y_max_field.value)

                # min < max のチェック
                if min_x >= max_x:
                    raise ValueError("x_min は x_max より小さい必要があります")
                if min_y >= max_y:
                    raise ValueError("y_min は y_max より小さい必要があります")

                # 0 が領域内に入るチェック
                if not (min_x <= 0 <= max_x):
                    raise ValueError("0 が x の領域内に入るようにしてください")
                if not (min_y <= 0 <= max_y):
                    raise ValueError("0 が y の領域内に入るようにしてください")

                # Δx と Δy の一致チェック
                dx = (max_x - min_x) / Nx
                dy = (max_y - min_y) / Ny

                if abs(dx - dy) > 1e-12:
                    raise ValueError(
                        f"Δx と Δy が一致しません（Δx={dx:.6f}, Δy={dy:.6f}）。"
                        " Nx, Ny または min/max の値を調整してください。"
                    )

                # geometry が領域内に収まっているかチェック
                geom_x = loaded_geometry[:, 0]
                geom_y = loaded_geometry[:, 1]

                if np.min(geom_x) < min_x or np.max(geom_x) > max_x:
                    raise ValueError(
                        f"geometry の x 座標が領域外です。\n"
                        f"geometry_x_min={np.min(geom_x):.6f}, geometry_x_max={np.max(geom_x):.6f}\n"
                        f"x_min={min_x}, x_max={max_x}"
                    )

                if np.min(geom_y) < min_y or np.max(geom_y) > max_y:
                    raise ValueError(
                        f"geometry の y 座標が領域外です。\n"
                        f"geometry_y_min={np.min(geom_y):.6f}, geometry_y_max={np.max(geom_y):.6f}\n"
                        f"y_min={min_y}, y_max={max_y}"
                    )

            except Exception as ex:
                result_text.value = f"⚠️ 入力エラー: {ex}"
                page.update()
                return

            # 実際の計算関数を呼び出す
            levelset_result, _, _ = geom_calc.culc_initial_levelset(
                loaded_geometry,
                min_x, min_y,
                max_x, max_y,
                Nx, Ny
            )

            page.session.store.set("levelset", levelset_result)
            page.session.store.set("Nx", Nx)
            page.session.store.set("Ny", Ny)
            page.session.store.set("min_x", min_x)
            page.session.store.set("min_y", min_y)
            page.session.store.set("max_x", max_x)
            page.session.store.set("max_y", max_y)

            result_text.value = "距離関数の計算が完了しました"

            # 画像表示
            levelset_image.src = IterationLogger.plot_levelset(levelset_result, min_x, max_x, min_y, max_y)
            levelset_image.visible = True

            page.update()

        def export_levelset_csv():
            # 計算結果があるかチェック
            if page.session.store.get("levelset") is None:
                result_text.value = "⚠️ 先に距離関数を計算してください"
                page.update()
                return

            levelset = page.session.store.get("levelset")

            geometry_filename = page.session.store.get("loaded_geometry_filename")

            # 1行目：geometry のファイル名
            header1 = geometry_filename

            # 2行目：計算時の設定
            header2 = (
                f"min_x={page.session.store.get("min_x")}, "
                f"max_x={page.session.store.get("max_x")}, "
                f"min_y={page.session.store.get("min_y")}, "
                f"max_y={page.session.store.get("max_y")}, "
                f"Nx={page.session.store.get("Nx")}, "
                f"Ny={page.session.store.get("Ny")}"
            )

            # ファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"levelset_output_{timestamp}.csv"

            # CSV 出力
            with open(filename, "w") as f:
                f.write(header1 + "\n")
                f.write(header2 + "\n")
                np.savetxt(f, levelset, fmt="%.6f", delimiter=",")

            # png出力
            filename_png = save_levelset_png_from_base64(levelset_image.src)

            result_text.value = f"levelset を CSV 出力しました: {filename}\n levelset の PNG を保存しました: {filename_png}"

            page.update()

        def save_levelset_png_from_base64(base64_src):
            # "data:image/png;base64,XXXX" の "XXXX" 部分だけ取り出す
            # Flet側の保存形式の問題
            if base64_src.startswith("data:image"):
                base64_data = base64_src.split(",")[1]
            else:
                base64_data = base64_src

            # decode
            img_bytes = base64.b64decode(base64_data)

            # ファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imageoutput\\levelset_plot_{timestamp}.png"

            # 保存
            with open(filename, "wb") as f:
                f.write(img_bytes)

            return filename

        return ft.View(
            route="/levelset_calc",
            controls=[
                build_header("/levelset_calc"),
                ft.Row(
                    controls=[
                        # 左側：テキスト・ボタン類
                        ft.Column(
                            controls=[
                                ft.Text("levelset関数計算ページ", size=24),

                                ft.Button(
                                    content="Pick csv file",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    on_click=pick_csv_file,
                                    bgcolor="#415FA0",
                                    color="#C0CAF5",
                                    style=ft.ButtonStyle(
                                        overlay_color="#2D3F64",
                                        shadow_color="#000000",
                                    ),
                                ),
                                selected_file_name,
                            ],
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),

                        # 中央列：6つの入力フィールド
                        ft.Column(
                            [
                                Nx_field,
                                Ny_field,
                                x_min_field,
                                x_max_field,
                                y_min_field,
                                y_max_field,
                                ft.Row(
                                        [
                                            ft.Button(
                                                "距離関数を計算", 
                                                on_click=run_distance_calc,
                                                bgcolor="#415FA0",
                                                color="#C0CAF5",
                                                style=ft.ButtonStyle(
                                                    overlay_color="#2D3F64",
                                                    shadow_color="#000000",
                                                ),
                                            ),
                                            ft.Button(
                                                "levelset CSV 出力", 
                                                on_click=export_levelset_csv,
                                                bgcolor="#48865D",
                                                color="#C0CAF5",
                                                style=ft.ButtonStyle(
                                                    overlay_color="#2F533B",
                                                    shadow_color="#000000",
                                                ),
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                    ),
                                result_text,
                            ],
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),

                        # 右側：画像表示
                        ft.Column(
                            controls=[
                                loaded_geometry_image,
                                levelset_image,
                            ],
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    expand=True,
                )
            ]
        )

    def initial_condition_view():
        inputs = {
                    "F_req": ft.TextField(label="要求推力 [N]", width=150, value=650),
                    "Pc_def": ft.TextField(label="初期燃焼室圧力 [MPa]", width=150, value=2),
                    "OF_def": ft.TextField(label="初期O/F比", width=150, value=6.5),
                    "mdot_new": ft.TextField(label="初期流量 [kg/s]", width=150, value=0.33),
                    "eta_cstar": ft.TextField(label="C*効率", width=150, value=0.8),
                    "eta_nozzle": ft.TextField(label="ノズル効率", width=150, value=1),
                }

        Nx_field    = ft.TextField(label="x方向の分割値", width=200, value = 600)
        Ny_field    = ft.TextField(label="y方向の分割値", width=200, value = 600)
        x_min_field = ft.TextField(label="x_min", width=200, value = -0.001)
        x_max_field = ft.TextField(label="x_max", width=200, value = 0.001)
        y_min_field = ft.TextField(label="y_min", width=200, value = -0.001)
        y_max_field = ft.TextField(label="y_max", width=200, value = 0.001)
        selected_file_name = ft.Text("No file selected")
        
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
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        
        def rho_change(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        # Dropdown 本体
        material_dropdown = ft.Dropdown(
            key = "material select",
            options = on_material_change(),
            width=250,
            on_select = rho_select,
            on_text_change = rho_change,
        )

        property_column = ft.Column(controls=[density_text, a_text, n_text], spacing=5)

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

        pressure_input.on_change = on_pressure_change

        async def pick_csv_file(_: ft.Event[ft.Button]):
            files = await ft.FilePicker().pick_files(
                allow_multiple=False,
                with_data=True,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
            )
            if not files:
                selected_file_name.value = "Selection cancelled"
                return
    
            selected = files[0]
            selected_file_name.value = f"Selected: {selected.name} ({selected.size} bytes)"
            raw = (
                selected.bytes.decode("utf-8", errors="replace") if selected.bytes else ""
            )
            loaded_geometry = np.loadtxt(StringIO(raw), delimiter=",")

            page.session.store.set("loaded_geometry_filename", selected.name)
            page.session.store.set("loaded_geometry", loaded_geometry)

        def run_simulation(e):
            try:
                # --- TextField から数値を取得 ---
                F_req      = float(inputs["F_req"].value)
                Pc_def     = float(inputs["Pc_def"].value)
                OF_def     = float(inputs["OF_def"].value)
                mdot_new   = float(inputs["mdot_new"].value)
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

                # geometryの構築
                loaded_geometry = page.session.store.get("loaded_geometry")
                
                # 型チェック + 正の値チェック
                Nx = validate_positive_int(Nx_field.value, "Nx（x方向の分割数）")
                Ny = validate_positive_int(Ny_field.value, "Ny（y方向の分割数）")
                min_x = float(x_min_field.value)
                min_y = float(y_min_field.value)
                max_x = float(x_max_field.value)
                max_y = float(y_max_field.value)

                # min < max のチェック
                if min_x >= max_x:
                    raise ValueError("x_min は x_max より小さい必要があります")
                if min_y >= max_y:
                    raise ValueError("y_min は y_max より小さい必要があります")

                # 0 が領域内に入るチェック
                if not (min_x <= 0 <= max_x):
                    raise ValueError("0 が x の領域内に入るようにしてください")
                if not (min_y <= 0 <= max_y):
                    raise ValueError("0 が y の領域内に入るようにしてください")

                # Δx と Δy の一致チェック
                dx = (max_x - min_x) / Nx
                dy = (max_y - min_y) / Ny

                if abs(dx - dy) > 1e-12:
                    raise ValueError(
                        f"Δx と Δy が一致しません（Δx={dx:.6f}, Δy={dy:.6f}）。"
                        " Nx, Ny または min/max の値を調整してください。"
                    )

                # geometry が領域内に収まっているかチェック
                geom_x = loaded_geometry[:, 0]
                geom_y = loaded_geometry[:, 1]

                if np.min(geom_x) < min_x or np.max(geom_x) > max_x:
                    raise ValueError(
                        f"geometry の x 座標が領域外です。\n"
                        f"geometry_x_min={np.min(geom_x):.6f}, geometry_x_max={np.max(geom_x):.6f}\n"
                        f"x_min={min_x}, x_max={max_x}"
                    )

                if np.min(geom_y) < min_y or np.max(geom_y) > max_y:
                    raise ValueError(
                        f"geometry の y 座標が領域外です。\n"
                        f"geometry_y_min={np.min(geom_y):.6f}, geometry_y_max={np.max(geom_y):.6f}\n"
                        f"y_min={min_y}, y_max={max_y}"
                    )

                geometry_setup = {
                    "min_x": min_x,
                    "min_y": min_y,
                    "max_x": max_x, 
                    "max_y": max_y,
                    "Nx": Nx,
                    "Ny": Ny,
                }

            except Exception as ex:
                result_text.value = f"⚠️ 入力エラー: {ex}"
                page.update()
                return

            print("input definition done. start calculation")

            output, Dovalue, cdvalue = sim_lev.initial_convergence(
                F_req,
                Pc_def,
                OF_def,
                mdot_new,
                eta_cstar,
                eta_nozzle,
                Ptank_init,
                rho_ox_init,
                rho_f_start,
                a_ox,
                n_ox,
                fuel_material,
                loaded_geometry,
                geometry_setup
            )
            # --- 結果表示 ---
            result_text.value = output

            # グラフ画像の取得
            graph_image.src = sim_lev.get_iteration_plot_base64(Dovalue, cdvalue)
            graph_image.visible = True

            # 画像の保存
            # base64 → バイナリに変換
            image_bytes = base64.b64decode(graph_image.src)

            # 保存先（相対パス）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imageoutput\\init_result_graph_{timestamp}.png"

            # PNG として保存
            with open(filename, "wb") as f:
                f.write(image_bytes)

            page.session.store.set("Pc_def", Pc_def)
            page.session.store.set("eta_cstar", eta_cstar)
            page.session.store.set("eta_nozzle", eta_nozzle)
            page.session.store.set("OF_def", OF_def)
            page.session.store.set("Ptank_init", Ptank_init)
            page.session.store.set("rho_ox_init", rho_ox_init)
            page.session.store.set("fuel_material", fuel_material)

            results_parsed = parse_initial_results(output)

            page.session.store.set("Kstar", results_parsed["Kstar"])
            page.session.store.set("epsilon", results_parsed["epsilon"])
            page.session.store.set("Lf", results_parsed["Lf"])
            page.session.store.set("mdot", results_parsed["mdot"])
            page.session.store.set("F", results_parsed["F"])
            page.session.store.set("Dt", results_parsed["Dt"])
            
            page.update()

        # 実行ボタンと遷移ボタンを並べる
        action_row = ft.Row(
            [
                ft.Button(
                        "収束計算", 
                        on_click=run_simulation,
                        bgcolor="#415FA0",
                        color="#C0CAF5",
                        style=ft.ButtonStyle(
                            overlay_color="#2D3F64",
                            shadow_color="#000000",
                        ),
                    ),
            ],
            alignment=ft.MainAxisAlignment.START,
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

        # 中央：geometryのsetup
        geometry_column = ft.Column(
            [
                Nx_field,
                Ny_field,
                x_min_field,
                x_max_field,
                y_min_field,
                y_max_field,
                ft.Button(
                    content="Pick csv file",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=pick_csv_file,
                    bgcolor="#415FA0",
                    color="#C0CAF5",
                    style=ft.ButtonStyle(
                        overlay_color="#2D3F64",
                        shadow_color="#000000",
                    ),
                ),

                selected_file_name,
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # 右側：収束グラフと K* グラフを縦に並べる
        graph_column = ft.Column(
            controls=[graph_image],
            spacing=10,
            expand=True,
            height=page.height + 100,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )

        return ft.View(
            route="/levelset_initial_condition",
            controls=[
                build_header("/levelset_initial_condition"),
                ft.Row(
                    controls=[input_column,  geometry_column, graph_column],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            ],
        )

    def evo_condition_view():
        results_graph_image = ft.Image(src= "", visible=False, width=600)

        # 初期値がある場合は値を埋める、なければ空欄
        Pc_def        = str(page.session.store.get("Pc_def")) 
        eta_cstar     = str(page.session.store.get("eta_cstar")) 
        eta_nozzle    = str(page.session.store.get("eta_nozzle")) 
        OF_def        = str(page.session.store.get("OF_def")) 
        Pt_init       = str(page.session.store.get("Ptank_init")) 
        rho_ox        = str(page.session.store.get("rho_ox_init")) 
        fuel_material = str(page.session.store.get("fuel_material")) 

        Kstar   = str(page.session.store.get("Kstar")) 
        epsilon = str(page.session.store.get("epsilon")) 
        Lf      = str(page.session.store.get("Lf")) 
        mdot    = str(page.session.store.get("mdot")) 
        F       = str(page.session.store.get("F")) 
        Dt      = str(page.session.store.get("Dt")) 

        # 入力欄の定義
        Pc_box         = ft.TextField(label="燃焼室圧力 Pc [MPa]", value=Pc_def, width=150)
        OF_box         = ft.TextField(label="初期OF比", value=OF_def, width=150)
        eta_cstar_box  = ft.TextField(label="C*効率", value=eta_cstar, width=150)
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
        a_text       = ft.Text()
        n_text       = ft.Text()

        def rho_select(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        
        def rho_change(e):
            # Dropdownで選択したmaterialの抽出
            selected_material = e.data
            #データ検索と物性値の取得
            for m in materials:
                if m["name"] == selected_material:
                    selected_properties = m
            # text出力
            density_text.value = f"密度: {selected_properties['rho']}"
            a_text.value       = f"a: {selected_properties['a']}"
            n_text.value       = f"n: {selected_properties['n']}"
        # Dropdown 本体
        material_dropdown = ft.Dropdown(
            key = "material select",
            options = on_material_change(),
            value = fuel_material,
            width = 150,
            on_select = rho_select,
            on_text_change = rho_change,
        )

        property_column = ft.Column(controls=[density_text, a_text, n_text], spacing=5)

        Kstar_box   = ft.TextField(label="K*", value=Kstar, width=150)
        epsilon_box = ft.TextField(label="膨張比 ε", value=epsilon, width=150)
        Lf_box      = ft.TextField(label="燃焼長 Lf [m]", value=Lf, width=150)
        mdot_box    = ft.TextField(label="推進剤流量 mdot [kg/s]", value=mdot, width=150)
        F_box       = ft.TextField(label="初期推力F [N]", value=F, width=150)
        Dt_box      = ft.TextField(label="スロート径 [m]", value=Dt, width=150)

        # タンク容積と最終酸化剤圧力の入力欄
        tank_volume_input      = ft.TextField(label="タンク容積 [m³]", width=150)
        initial_pressure_input = ft.TextField(label="初期酸化剤圧力 [MPa]", value=Pt_init,width=150)
        rho_ox_input           = ft.TextField(label="初期酸化剤密度(圧力をいじる場合は調整してください．) [kg/s]", value=rho_ox,width=150)
        final_pressure_input   = ft.TextField(label="最終酸化剤圧力 [MPa]", width=150)
        cea_input              = ft.TextField(label="CEA更新頻度", width=150)

        # calc areaとlevelsetの入力欄
        selected_file_name = ft.Text("No file selected")
        x_min_field = ft.TextField(label="x_min", width=200, value = -0.001)
        x_max_field = ft.TextField(label="x_max", width=200, value = 0.001)
        y_min_field = ft.TextField(label="y_min", width=200, value = -0.001)
        y_max_field = ft.TextField(label="y_max", width=200, value = 0.001)


        async def pick_csv_file(_: ft.Event[ft.Button]):
            files = await ft.FilePicker().pick_files(
                allow_multiple=False,
                with_data=True,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
            )
            if not files:
                selected_file_name.value = "Selection cancelled"
                return

            selected = files[0]
            selected_file_name.value = f"Selected: {selected.name} ({selected.size} bytes)"
            raw = (
                selected.bytes.decode("utf-8", errors="replace") if selected.bytes else ""
            )
            loaded_geometry = np.loadtxt(StringIO(raw), delimiter=",", skiprows=2)

            page.session.store.set("levelset_filename", selected.name)
            page.session.store.set("levelset", loaded_geometry)

        csv_download_button = ft.Button(
            "CSV出力 ⬇",
            icon=ft.Icons.DOWNLOAD,
            visible=False,
            on_click=lambda _: None,
            bgcolor="#48865D",
            color="#C0CAF5",
            style=ft.ButtonStyle(
                overlay_color="#2F533B",
                shadow_color="#000000",
            ),
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
                "C* [m/s]",
                "CF [-]",
                "tank mass [g]",
                "mdot_ox [g/ms]",
                "gamma [-]",
                "Af [m^2]"
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
        def on_run_simulation(e):
            try:
                # 各入力欄から値を取得
                Pc            = float(Pc_box.value)
                OF            = float(OF_box.value)
                eta_cstar     = float(eta_cstar_box.value)
                eta_nozzle    = float(eta_nozzle_box.value)
                Kstar         = float(Kstar_box.value)
                epsilon       = float(epsilon_box.value)
                Lf            = float(Lf_box.value)
                mdot          = float(mdot_box.value)
                V_tank        = float(tank_volume_input.value)
                P_init        = float(initial_pressure_input.value)
                P_final       = float(final_pressure_input.value)
                F_init        = float(F_box.value)
                Dt            = float(Dt_box.value)
                rho_ox        = float(rho_ox_input.value)
                fuel_material = material_dropdown.value

                for m in materials:
                    if m["name"] == fuel_material:
                        props = m
                
                rho_f        = float(props["rho"])
                a_ox         = float(props["a"])
                n_ox         = float(props["n"])
                cea_interval = float(cea_input.value)

                levelset = page.session.store.get("levelset")

                min_x = float(x_min_field.value)
                min_y = float(y_min_field.value)
                max_x = float(x_max_field.value)
                max_y = float(y_max_field.value)

                # min < max のチェック
                if min_x >= max_x:
                    raise ValueError("x_min は x_max より小さい必要があります")
                if min_y >= max_y:
                    raise ValueError("y_min は y_max より小さい必要があります")

                # 0 が領域内に入るチェック
                if not (min_x <= 0 <= max_x):
                    raise ValueError("0 が x の領域内に入るようにしてください")
                if not (min_y <= 0 <= max_y):
                    raise ValueError("0 が y の領域内に入るようにしてください")

                calc_area = [[float(min_x),float(max_x)],[float(min_y),float(max_y)]]

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
                ) = sim_lev.integration_simulation(
                    Pc            = Pc,
                    lvlset_file   = levelset,
                    OF            = OF,
                    eta_cstar     = eta_cstar,
                    eta_nozzle    = eta_nozzle,
                    Kstar         = Kstar,
                    epsilon       = epsilon,
                    Lf            = Lf,
                    mdot          = mdot,
                    V_tank        = V_tank,
                    P_init        = P_init,
                    P_final       = P_final,
                    rho_ox        = rho_ox,
                    rho_fuel      = rho_f,
                    a             = a_ox,
                    n             = n_ox,
                    fuel_material = fuel_material,
                    F             = F_init,
                    Dt            = Dt,
                    culc_area     = calc_area,
                    cea_interval  = cea_interval
                )

                # 結果表示（仮）
                evolution_output.value = f"✅ 計算完了, Total Inpulse = {It}[Ns], 燃焼時間{tb}[sec], Isp{Isp}[s]"
            except Exception as ex:
                evolution_output.value = f"⚠️ 計算エラー: {ex}"
                print(ex)
            
            input_params = [
                ("Pc", Pc), ("OF", OF),
                ("eta_cstar", eta_cstar), ("eta_nozzle", eta_nozzle), ("Kstar", Kstar),
                ("epsilon", epsilon), ("Lf", Lf), ("mdot", mdot),
                ("V_tank", V_tank), ("P_init", P_init), ("P_final", P_final),
                ("rho_ox", rho_ox), ("rho_fuel", rho_f),
                ("a", a_ox), ("n", n_ox), ("F", F_init), ("Dt", Dt),
                ("Fuel Material",fuel_material), ("levelset file",page.session.store.get("levelset_filename"))
            ]

            performance_params = [
                ("It", It), ("Tb", tb), ("Isp", Isp) 
            ]
            def on_csv_download_click(e):
                csv_data_url = get_csv_download_link(input_params, performance_params, evolution_result)

            # 結果csvのダウンロード処理
            csv_download_button.on_click = on_csv_download_click
            csv_download_button.visible = True

            # resultのグラフ描画
            results_graph_image.src = sim.get_evolution_plot_base64(
                time_ms, F_arr, F_fte_arr, OF_arr, Cstar_arr, Pc_arr, Pt_arr
            )
            results_graph_image.visible = True

            # 画像の保存
            # base64 → バイナリに変換
            image_bytes = base64.b64decode(results_graph_image.src)

            # 保存先（相対パス）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imageoutput\\evo_result_graph_{timestamp}.png"

            # PNG として保存
            with open(filename, "wb") as f:
                f.write(image_bytes)
            page.update()

        run_button = ft.Button(
            "時間発展計算 ▶", 
            on_click=on_run_simulation,
            bgcolor="#415FA0",
            color="#C0CAF5",
            style=ft.ButtonStyle(
                overlay_color="#2D3F64",
                shadow_color="#000000",
            ),
        )
        evolution_output = ft.Text("🕒 時間発展シミュレーション")

        return ft.View(
            route="/levelset_evo_condition",
            controls=[
                build_header("/levelset_evo_condition"),
                ft.Text("時間発展ページ", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        # 1列目
                        ft.Column(
                            [
                                ft.Text("初期状態パラメータ①："),
                                Pc_box,
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
                        # 4列目
                        ft.Column(
                            [
                                ft.Text("初期状態パラメータ④："),
                                x_min_field,
                                x_max_field,
                                y_min_field,
                                y_max_field,
                                ft.Button(
                                    content="Pick csv file",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    on_click=pick_csv_file,
                                    bgcolor="#415FA0",
                                    color="#C0CAF5",
                                    style=ft.ButtonStyle(
                                        overlay_color="#2D3F64",
                                        shadow_color="#000000",
                                    ),
                                ),
                                selected_file_name,
                            ],
                            spacing=10,
                        ),
                        # ✅ 5列目：グラフ表示
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
            ],
        )

    # ページ切り替え処理
    def route_change():
        page.views.clear()
        # 初期の形状選択画面
        if page.route == "/shape_select":
            page.views.append(shape_select_view())
        # 円形ポート計算用の初期画面
        elif page.route == "/main":
            page.views.append(main_view())
        # 円形ポート計算用の時間発展画面
        elif page.route == "/evolution":
            page.views.append(evolution_view())
        # geometry点群計算用の初期画面
        elif page.route == "/noncircular":
            page.views.append(noncircular_geometry_view())
        # levelset関数計算画面
        elif page.route == "/levelset_calc":
            page.views.append(levelset_calc_view())
        # levelsetによる初期条件計算
        elif page.route == "/levelset_initial_condition":
            page.views.append(initial_condition_view())
        # levelsetによる時間発展計算
        elif page.route == "/levelset_evo_condition":
            page.views.append(evo_condition_view())
        page.update()

    page.route = "/shape_select"
    page.on_route_change = route_change()
    page.update()

ft.run(main)