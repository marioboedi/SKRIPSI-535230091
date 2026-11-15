# Jakarta Siaga

Dashboard Streamlit berbahasa Indonesia untuk skripsi **Klasterisasi Kelurahan Berdasarkan Indikator Kerawanan Kebakaran di DKI Jakarta Menggunakan Metode K-Means, Hierarchical Clustering, dan Spectral Bridges**. Menggunakan dataset asli `2425.csv` yang disediakan: **534 observasi, 267 kelurahan, 2024–2025**, pada enam wilayah administrasi.

## Menjalankan aplikasi di Windows

Klik dua kali **run_app.bat**, lalu buka **http://localhost:8501**. Jendela peluncur perlu tetap terbuka selama aplikasi digunakan. Tekan **Ctrl+C** pada jendela itu untuk menghentikan aplikasi.

Lingkungan `.venv` sudah disiapkan pada perangkat ini. Pada perangkat baru, gunakan **Python 3.11 atau 3.12**. Peluncur membuat lingkungan proyek dan memasang dependensi bila belum tersedia. Instalasi pertama membutuhkan internet. Untuk menjalankan secara manual dari folder proyek:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Jika Python tidak terdaftar pada `py`, ganti `py -3.11` dengan jalur interpreter Python 3.11/3.12. Python 3.14 tidak ditargetkan oleh dependensi numerik yang dikunci di proyek ini.

## Halaman dan alur penggunaan

- **Beranda:** ringkasan hasil algoritma berperingkat terbaik, peta kelurahan, komposisi profil, perbandingan wilayah, penjelasan indikator, dan tujuan penelitian.
- **Dataset:** data mentah interaktif, autocomplete kelurahan/kecamatan, filter tahun/wilayah, satu tombol **Data Terbaru** menuju Google Drive, ekspor CSV melalui menu tabel, unggahan tervalidasi, serta tombol kembali ke dataset awal.
- **Klasterisasi:** tab ketiga metode, peta dan hasil tiap kelurahan, autocomplete, rincian sembilan indikator, profil centroid, kepadatan, tiga grafik evaluasi kandidat K beserta penanda model final, laporan ZIP, serta tab **Analisis data** dengan korelasi, histogram/KDE/boxplot, perbandingan klaster, profil rata-rata, jumlah anggota, dan proyeksi PCA. Expander **Bandingkan performa ketiga algoritma** memuat tabel perbandingan metrik. Tombol **Silhouette Plot** di bawah nilai Silhouette Score pada setiap tab algoritma membuka panel berisi pilihan algoritma dan satu Silhouette Plot gabungan seluruh klaster final. Tab **Analisis data → Distribusi** juga memuat boxplot distribusi indikator menurut klaster final algoritma yang dipilih. Grafik Analisis data dan Silhouette Plot dapat diunduh sebagai PNG.
- **FAQ:** panduan membaca hasil dan mekanisme analisis.
- **Tentang aplikasi:** latar belakang, pengembang, dan dosen pembimbing.

Unggahan CSV yang valid langsung menjadi dataset aktif bagi seluruh halaman. Unggahan yang gagal tidak mengganti data sebelumnya. Filter hanya mengubah tampilan; seluruh dataset aktif tetap digunakan untuk pemodelan. Dataset berlaku selama sesi. Sesi baru kembali memakai CSV bawaan.

## Metodologi yang diterapkan

1. **Validasi** kolom, nilai numerik hingga keterbatasan koordinat global, persentase 0–100, identitas wilayah, dan keunikan kombinasi tahun/wilayah. Nilai kosong tidak diimputasi secara diam-diam.
2. **Z-score per tahun:** setiap indikator distandardisasi secara terpisah pada masing-masing tahun menggunakan `StandardScaler` (simpangan baku populasi, `ddof=0`). Pada data bawaan, rata-rata dan simpangan baku 2024 dihitung dari observasi 2024, begitu pula 2025. Standardisasi dilakukan **sebelum agregasi**. Indikator konstan pada suatu tahun memiliki Z-score 0 dan diberi catatan.
3. **Agregasi rata-rata** Z-score antarperiode berdasarkan `kota + kecamatan + kelurahan`, lalu diurutkan menurut ketiga kolom tersebut agar inisialisasi acak dapat direproduksi. Pada data bawaan, 534 observasi menjadi 267 baris. Persentase asli, kepadatan, koordinat, dan elevasi juga dirata-ratakan antarperiode untuk profil hasil. Data dengan periode tidak lengkap diberi catatan.
4. **Masukan model:** hanya empat indikator listrik dan lima indikator gas dalam bentuk Z-score agregasi. Tahun, kepadatan, lokasi, dan identitas wilayah tidak dimasukkan sebagai fitur klasterisasi.
5. **Pencarian K=2–10** pada setiap metode. Kandidat dengan jumlah anggota/klaster tidak valid dikeluarkan dan alasannya ditampilkan. Untuk dataset kecil, K dibatasi sampai `n−1`. Spectral Bridges memerlukan sedikitnya 15 kelurahan dengan pola indikator berbeda agar `n_nodes=15` tetap digunakan.
6. **Pemilihan K:** Silhouette tertinggi, DBI terendah, dan CHI tertinggi memberikan masing-masing satu suara. Mayoritas minimal dua suara menang. **Asumsi tambahan untuk kasus yang tidak ditentukan prompt:** jika ketiga metrik memilih K berbeda, gunakan rata-rata peringkat metrik terendah, lalu Silhouette lebih tinggi, lalu K lebih kecil. Jika satu metrik seri, K terkecil memenangkan suara metrik tersebut. Perhitungan memakai presisi penuh; tampilan dibulatkan.
7. **Model final** dihitung kembali dengan K terpilih. Tiga metrik dihitung dari label final, bukan disalin dari contoh.
8. **Interpretasi:** rata-rata empat centroid Z-score listrik menghasilkan `Risk_Listrik`; rata-rata lima centroid gas menghasilkan `Risk_Gas`. Jika hanya listrik >0,5: Dominan Bahaya Kelistrikan; hanya gas >0,5: Dominan Bahaya Gas; keduanya >0,5: Dominan Bahaya Keduanya; keduanya ≤0,5: Risiko Rendah. Semua kelurahan dalam klaster menerima interpretasi centroid yang sama.
9. **Peringkat algoritma:** rata-rata peringkat tiga metrik final terendah ditampilkan lebih dahulu; jika seri, Silhouette lebih tinggi, lalu nama algoritma. Skor metrik dengan skala berbeda tidak dijumlahkan. Ini adalah aturan penyajian yang ditambahkan untuk membuat kata “optimal” pada prompt dapat dioperasionalkan.

| Metode | Parameter tetap |
| --- | --- |
| K-Means | `random_state=11`, `n_init=10` |
| AHC | `linkage='ward'`, jarak Euclidean |
| Spectral Bridges | paket asli `spectral-bridges==1.3.0`, `random_state=549`, `n_nodes=15`, `p=2` |

Nomor klaster diurutkan dari rata-rata centroid sembilan indikator tertinggi untuk mempermudah pembacaan; perubahan nomor tidak mengubah kelompok. Nomor antaralgoritma tidak dapat dicocokkan langsung. **Risiko Rendah adalah label relatif pada indikator, bukan kepastian bebas kebakaran, status resmi, atau probabilitas kejadian.** Profil kepadatan memakai kategori deskriptif aplikasi: ≤10.000 jiwa/km²; padat >10.000–20.000; sangat padat >20.000. Kategori ini bukan klasifikasi resmi kerawanan.

## Peta, unduhan, dan cache

Peta memadukan latar geografis **CARTO Voyager/OpenStreetMap**, batas administrasi lokal, label enam wilayah, dan **titik profil kerawanan kelurahan**. Batas asli [DPMPTSP DKI Jakarta](https://gis-dpmptsp.jakarta.go.id/arcgis/rest/services/Hosted/Batas_Administrasi_Kelurahan_DKI_Jakarta/FeatureServer/85) mencakup **267 kelurahan, 44 kecamatan, dan 6 kota/kabupaten**; batas disederhanakan untuk visualisasi, bukan penetapan hukum. Beranda menampilkan provinsi/kota/kecamatan, sedangkan Klasterisasi memiliki tombol Batas kelurahan. Latitude/longitude menentukan posisi titik; elevasi dapat ditampilkan sebagai posisi vertikal dalam mode elevasi. Data Kepulauan Seribu tetap tercakup; gunakan filter wilayah untuk menelusurinya atau geser/perkecil peta. Jika hasil filter berada di luar cakupan daratan awal, peta otomatis menyesuaikan pusat dan zoom. Batas tersedia tanpa internet; latar geografis dan font eksternal membutuhkan internet. Aplikasi tidak mengirim dataset ke layanan batas wilayah. Sumber dan tanggal pengambilan tersimpan pada `assets/boundaries/source.json`. Untuk membangun ulang aset: `python scripts/prepare_boundaries.py --download`.

Diagram di Beranda dan Klasterisasi memakai jumlah kelurahan asli sebagai proporsi. Jarak antaririsan dan pembulatan ujung dihilangkan agar irisan satu kelurahan tidak tertutup. Beranda merangkum empat kategori risiko, sedangkan Klasterisasi menampilkan seluruh klaster dari model beserta profil masing-masing. Jumlah dan persentase memakai total kelurahan yang sedang ditampilkan. Proporsi di bawah 1% diberi keterangan tambahan; ukuran irisan tidak diperbesar. Tombol **Data Terbaru** memakai URL Drive yang sama seperti sebelumnya; unduhan dataset lokal yang duplikat dihapus.

Di Klasterisasi, pilihan **Klaster / Profil kerawanan** digabung menjadi **Sebaran klaster dan profil** untuk AHC, K-Means, dan Spectral Bridges. Satu ringkasan backend berdasarkan kolom `klaster` dari hasil model final menjadi sumber diagram, label, profil, jumlah, serta persentase. Setiap klaster ditampilkan satu kali dalam urutan nomor, dengan warna yang sama pada peta dan diagram. Keterangannya memuat **Klaster N**, **jumlah kelurahan dan persentase**, lalu **Profil kerawanan: interpretasi dari centroid**. Klaster yang memiliki profil sama tetap terpisah. AHC bawaan memiliki tiga rincian: klaster 1 Dominan Bahaya Gas, 1 kelurahan (0,4%); klaster 2 Risiko Rendah, 128 kelurahan (47,9%); klaster 3 Risiko Rendah, 138 kelurahan (51,7%). K-Means tetap memiliki tiga klaster dan Spectral Bridges dua klaster. Filter mengubah jumlah dan penyebut persentase sesuai kelurahan yang tampil; nomor dan hasil model tetap. Pemilihan algoritma, peta, rincian centroid, evaluasi, analisis data, serta unduhan dipertahankan.

Khusus AHC, keterangan membedakan **karakteristik centroid** dari **kategori risiko**. Klaster 2 bawaan memiliki 9/9 centroid indikator di atas rata-rata tahunan; Klaster 3 memiliki 9/9 di bawahnya. Keduanya tetap berkategori Risiko Rendah karena indeks listrik/gas masing-masing ≤0,5: 0,338/0,434 dan −0,306/−0,449. Modul audit memeriksa pemetaan lewat identitas kelurahan, menghitung ulang centroid anggota, dan menolak profil yang tertukar. Dasar perhitungan serta sembilan centroid tersedia pada **Dasar interpretasi AHC**. Lihat [audit interpretasi AHC](docs/AUDIT_INTERPRETASI_AHC.md).

Hasil disimpan dalam cache dengan isi dataset sebagai kunci (maksimum delapan dataset, kedaluwarsa satu jam). Mengubah filter tidak menjalankan ulang pemodelan. Parameter algoritma tidak tersedia sebagai kontrol pengguna.

Autocomplete memakai `st.selectbox` dengan pencocokan substring tanpa membedakan huruf besar/kecil. Saran berasal dari kombinasi wilayah unik dataset aktif. Nama sama dibedakan oleh kecamatan/kota. Memilih saran menjalankan filter tepat; mengetik lalu Enter menjalankan pencarian bebas sebagian nama. Penyaringan saran berlangsung di browser, sehingga tidak memicu komputasi server per ketukan tombol.

Grafik analisis memakai seluruh kelurahan dataset aktif dan label model final. Korelasi/distribusi/perbandingan memakai rata-rata persentase asli antarperiode; PCA memakai Z-score agregasi yang benar-benar masuk model. Grafik dihasilkan hanya untuk tampilan terbuka dan di-cache terpisah (maksimum 24 grafik, satu jam). Nilai kosong/nonangka pada fungsi grafik diabaikan tanpa imputasi; validasi unggahan tetap menolak data tidak valid. Implementasi dan daftar library: [laporan PROMPT 03](docs/IMPLEMENTASI_PROMPT_03.md).

Laporan ZIP berisi hasil semua metode yang berhasil, profil centroid, eksperimen K, tabel perbandingan, data agregasi, Z-score agregasi, dan `metodologi.json`. Angka yang ditampilkan dihitung dari dataset aktif.

## Pengujian

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Seluruh **76 tes** mencakup standardisasi per tahun, validasi CSV, pemilihan K, centroid, tiga algoritma, navigasi/filter/unggahan, grafik analisis, proporsi donut, data Kepulauan Seribu, serta konsistensi ringkasan terpadu untuk ketiga algoritma. Data diagram yang benar-benar dikirim ke browser dibaca kembali dan dibandingkan dengan anggota serta profil klaster pada tabel hasil. Pengujian memastikan setiap klaster muncul satu kali dengan profil, jumlah, persentase, dan warna yang tepat, termasuk sesi yang masih menyimpan pilihan tampilan lama. Filter, urutan baris acak, dan nomor klaster berbeda diperiksa; konsistensi label Risiko Rendah dan fitur lain tetap dicakup. Tes regresi membandingkan seluruh **81 nilai metrik** dengan tabel eksperimen PROMPT 02 pada toleransi pembulatan empat desimal. Lihat [catatan reproduksi](docs/REPRODUKSI_PROMPT_02.md), [revisi PROMPT 04 serta visualisasi AHC](docs/REVISI_PROMPT_04_DAN_AHC.md), dan [penyeragaman legenda serta label](docs/REVISI_LEGENDA_DAN_LABEL.md).

Sebanyak **16 tes evaluasi** memeriksa skor pada grafik kandidat/final, Silhouette Plot gabungan per algoritma beserta rata-rata yang sama dengan kartu, boxplot indikator menurut klaster final, konsistensi tabel dan kartu, payload grafik Streamlit untuk semua algoritma, dataset unggahan, kandidat gagal, serta interaksi tanpa pelatihan ulang. Hasil perhitungan sebelum/sesudah perapihan identik di luar waktu eksekusi. Server aktual juga diuji melalui pemeriksaan kesehatan dan lima URL halaman; perilaku halaman diuji dengan AppTest. Rincian dan batas verifikasi: [panduan pengembangan](docs/PANDUAN_PENGEMBANGAN.md#hasil-verifikasi-perapihan).

## Struktur proyek

Panduan lokasi kode, konvensi nama, sumber nilai grafik, dan catatan pemindahan file: **[Panduan pengembangan](docs/PANDUAN_PENGEMBANGAN.md)**. Silhouette Plot per algoritma tersedia melalui tombol di dekat nilai Silhouette Score, kurva tiga metrik setiap algoritma ada di **Evaluasi & pemilihan K**, dan boxplot indikator per klaster ada di **Analisis data → Distribusi**. Skor final dan kandidat dibedakan; tidak ada nilai contoh atau perubahan metode/parameter.

```text
app.py                  # Navigasi dan bingkai aplikasi
app_pages/              # beranda.py, dataset.py, klasterisasi.py, faq.py, tentang.py
firewatch/analysis.py   # Validasi dan seluruh perhitungan penelitian
firewatch/state.py      # Dataset sesi dan cache
firewatch/charts.py     # Grafik Altair dan peta PyDeck
firewatch/evaluation_charts.py # Grafik tiga metrik: kandidat K dan perbandingan final
firewatch/evaluation_ui.py     # Panel evaluasi Streamlit dan interpretasinya
firewatch/eda.py        # Grafik Matplotlib/Seaborn, statistik, dan PCA
firewatch/geography.py  # Batas administrasi lokal
firewatch/palette.py    # Warna tetap per nomor klaster
firewatch/profiles.py   # Karakteristik dan label tampilan AHC
firewatch/regions.py    # Saran wilayah dan filter pencarian
firewatch/reports.py    # Serialisasi CSV dan laporan ZIP
firewatch/ui.py         # Komponen hasil, tabel, filter, dan rincian
assets/                 # Logo, ilustrasi, dan GeoJSON batas administrasi
docs/                   # Panduan dan catatan implementasi/audit
docs/screenshots/       # Bukti tampilan historis, bukan aset aplikasi
scripts/                # Penyiapan ulang aset geografis
.streamlit/config.toml  # Tema dan konfigurasi
tests/                  # Tes perhitungan dan antarmuka
2425.csv                # Dataset asli, tidak diubah
PROMPT.md               # Spesifikasi yang diberikan, tidak diubah
run_app.bat / .ps1      # Peluncur Windows, tetap di root
```

## Pengembang

**Mario Samuel Budiono (535230091)** — Teknik Informatika, Fakultas Teknologi Informasi, Universitas Tarumanagara. Dosen pembimbing: **Dr. Bagus Mulyawan, S.Kom., M.M.** Email: mario.535230091@stu.untar.ac.id.

Referensi implementasi: [Streamlit](https://docs.streamlit.io/), [scikit-learn](https://scikit-learn.org/stable/modules/clustering.html), dan [paket Spectral Bridges](https://pypi.org/project/spectral-bridges/).
