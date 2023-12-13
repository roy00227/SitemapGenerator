import tkinter as tk
from tkinter import font
from threading import Thread
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET
from datetime import datetime

# 訪れたURLを保持するセット
visited_urls = set()

class SitemapGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sitemap Generator")

        # ウィンドウの大きさを変更できないようにする
        self.root.resizable(width=False, height=False)

        # ラベルとエントリー
        tk.Label(self.root, text="Start URL:").pack(pady=5)
        self.start_url_entry = tk.Entry(self.root, width=80)
        self.start_url_entry.pack(pady=5)

        # 開始ボタン
        self.start_button = tk.Button(self.root, text="Start Crawling", command=self.start_crawling)
        self.start_button.pack(pady=10)

        # ページ数表示ラベル
        self.page_count_label_var = tk.StringVar()
        self.page_count_label_var.set("Pages Crawled: 0")
        self.page_count_label = tk.Label(self.root, textvariable=self.page_count_label_var)
        self.page_count_label.pack(pady=5)

        # メッセージ表示ラベル
        self.message_label_var = tk.StringVar()
        self.message_label_var.set("")
        self.message_label = tk.Label(self.root, textvariable=self.message_label_var, wraplength=500)
        self.message_label.pack(pady=5)


        # フレームを作成
        frame = tk.Frame(self.root)
        frame.pack()

        # URLリストボックス
        self.url_listbox = tk.Text(frame, height=10, width=80, wrap=tk.WORD)
        self.url_listbox.pack(side=tk.LEFT, pady=5)

        # スクロールバー
        scrollbar = tk.Scrollbar(frame, command=self.url_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # URLリストボックスにスクロールバーを結びつける
        self.url_listbox.config(yscrollcommand=scrollbar.set)


        # クラス変数としてstart_urlを追加
        self.start_url = ""
        self.crawling_thread = None  # クロール用のスレッド


    def is_valid_start_url(self, url):
        # スタートURLが空でないことを確認
        if not url:
            self.message_label_var.set("Error: Start URL is empty.")
            self.message_label.config(font=("TkDefaultFont"))
            self.message_label.config(fg="red")
            return False

        # HTTPリクエストを発行してアクセス可能か確認
        try:
            response = requests.get(url)
            response.raise_for_status()  # HTTPエラーレスポンスがあれば例外を発生させる

            # printステートメントを使用してステータスコードを表示
            # print(f"Status Code for {url}: {response.status_code}")

            # スタートURLが404エラーの場合、エラーメッセージを表示して中断
            # ステータスコードが404の場合はエラーメッセージを表示して終了
            if response.status_code == 404 or not response.ok:
                self.message_label_var.set(f"Error accessing Start URL: {response.status_code}")
                self.message_label.config(font=("TkDefaultFont"))
                self.message_label.config(fg="red")
                return

            return True
        except requests.exceptions.RequestException as e:
            self.message_label_var.set(f"Error accessing Start URL: {e}")
            self.message_label.config(font=("TkDefaultFont"))
            self.message_label.config(fg="red")
            return False


    def crawl_site(self, url, xml_element):
        try:

            # HTTPリクエストを発行
            response = requests.get(url)
            response.raise_for_status()  # HTTPエラーレスポンスがあれば例外を発生させる

            # 訪れたURLに追加
            visited_urls.add(url)

            # XML要素を作成して追加
            url_elem = ET.Element("url")
            loc_elem = ET.SubElement(url_elem, "loc")
            loc_elem.text = url

            # 更新日付を追加
            lastmod_elem = ET.SubElement(url_elem, "lastmod")
            lastmod_elem.text = datetime.now().strftime("%Y-%m-%d")

            # url_elem を xml_element に追加
            xml_element.append(url_elem)

            # 成功した場合のみページ数を表示
            self.page_count_label_var.set(f"Pages Crawled: {len(visited_urls)}")
                
            # URLリストボックスに追加
            self.url_listbox.insert(tk.END, url + "\n")
            #スクロールバーを一番下に移動
            self.url_listbox.yview(tk.END)

            # 更新
            self.root.update_idletasks()

            # HTMLを解析
            soup = BeautifulSoup(response.text, 'html.parser')

            # URLを抽出
            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                if href:
                    # ページ内リンクの場合、無視
                    if href.startswith('#'):
                        continue

                    # 相対パスを絶対URLに変換
                    abs_url = urljoin(url, href)

                    try:
                        # ドメインが一致し、まだ訪れていない場合のみ再帰的にクロール
                        if urlparse(abs_url).netloc == urlparse(self.start_url).netloc and abs_url not in visited_urls:
                            # 再帰的にクロール
                            self.crawl_site(abs_url, xml_element)
                    except requests.exceptions.RequestException as e:
                        # エラー
                        return

        except requests.exceptions.RequestException as e:
            # エラー
            return


    def crawling_thread_func(self):
        try:
            # 訪れたURLを保持するセットを初期化
            global visited_urls
            visited_urls = set()

            # URLリストボックスをクリア
            self.url_listbox.delete("1.0", tk.END)

            # XML要素を作成
            root_xml = ET.Element("urlset")
            root_xml.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

            # クロールを実行
            self.crawl_site(self.start_url, root_xml)

            # XMLツリーをファイルに書き込む
            tree = ET.ElementTree(root_xml)
            tree.write("sitemap.xml", encoding="utf-8", xml_declaration=True, method="xml")

        finally:
            # クロール終了後、メッセージを表示
            self.message_label_var.set("Crawling Completed!")
            # クロール終了後、太字のフォントにする
            self.message_label.config(font=("TkDefaultFont", 12, "bold"))
            self.message_label.config(fg="black")  # フォントカラーを黒に変更

            # クロール終了後、開始ボタンを有効化
            self.start_button.config(state=tk.NORMAL)

    def start_crawling(self):
        if self.crawling_thread and self.crawling_thread.is_alive():
            # 既にクロール中の場合は何もしない
            return

        # start_urlをクラス変数にセット
        self.start_url = self.start_url_entry.get()

        # スタートURLが無効な場合は中断
        if not self.is_valid_start_url(self.start_url):
            return

        # 開始ボタンを無効化
        self.start_button.config(state=tk.DISABLED)

        # クロール中のメッセージを表示
        self.message_label_var.set("Crawling...")

        # クロール中は普通のフォント
        self.message_label.config(font=("TkDefaultFont"))
        self.message_label.config(fg="black")  # フォントカラーを黒に変更

        # クロール用のスレッドを開始
        self.crawling_thread = Thread(target=self.crawling_thread_func)
        self.crawling_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SitemapGeneratorApp(root)

    # ウィンドウの幅と高さを指定
    width = 600
    height = 400

    # 画面の中央に配置
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    # geometryメソッドでウィンドウの位置とサイズを指定
    root.geometry(f"{width}x{height}+{x}+{y}")

    app.start_url_entry.focus_force()  # フォーカスをエントリーに設定
    root.mainloop()

# リンクボックスのリセットを修正。