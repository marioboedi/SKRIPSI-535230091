# Implementasi PROMPT 03 — Jakarta Siaga 1.2.0

Pengembangan mempertahankan pipeline penelitian 1.1.0: Z-score per tahun, rata-rata per kelurahan, parameter tiga algoritma, pemilihan K, dan interpretasi centroid. Penambahan berfokus pada peta, pencarian, serta visualisasi hasil.

## Peta Beranda dan Klasterisasi

- Latar geografis CARTO Voyager dengan jalan, pesisir, pulau, dan nama tempat berbasis OpenStreetMap.
- Batas resmi bersumber dari [DPMPTSP DKI Jakarta, layer 85](https://gis-dpmptsp.jakarta.go.id/arcgis/rest/services/Hosted/Batas_Administrasi_Kelurahan_DKI_Jakarta/FeatureServer/85): 267 kelurahan, 44 kecamatan, 6 kota/kabupaten. Sumber diambil pada 19 Oktober 2026; metadata pengambilan disimpan di `assets/boundaries/source.json`.
- Sumber berkoordinat UTM EPSG:32748 diambil melalui kueri keluaran EPSG:4326. Kota/kecamatan/provinsi dihasilkan dari penggabungan geometri sumber; geometri disederhanakan sekitar 0,00006–0,00008 derajat untuk visualisasi. Aset akhir sekitar 0,9 MB dan tersedia lokal, bukan ditarik ulang setiap sesi.
- Garis provinsi/kota lebih tebal dari kecamatan/kelurahan. Label kota menggunakan titik di dalam bagian daratan terluas. Lapisan titik kerawanan dirender terakhir dan tetap menerima tooltip. Warna kerawanan, legenda profil, pan, zoom, Kepulauan Seribu, dan elevasi dipertahankan.
- Detail kelurahan dapat diaktifkan di Klasterisasi. Peta Beranda menampilkan provinsi/kota/kecamatan agar ringkasan tetap terbaca.
- Latar geografis memerlukan internet; garis administrasi tidak. Batas bersifat referensi visual, bukan penetapan hukum. Aset geografis tidak menjadi fitur model dan tidak bergantung pada unggahan pengguna.

Membangun ulang aset dengan sumber publik: `.venv\Scripts\python.exe scripts\prepare_boundaries.py --download`.

## Autocomplete wilayah

`st.selectbox` menerima opsi baru dengan `filter_mode="contains"`. Saat pengguna mengetik, browser menyaring 267 kelurahan + 44 kecamatan pada dataset bawaan. Daftar ini selalu dibuat ulang dari wilayah unik dataset aktif; jumlah mengikuti data unggahan.

- Pencocokan substring tanpa membedakan kapital; dukungan mouse, panah, dan Enter dari widget native Streamlit.
- Nama opsi memuat kecamatan/kota agar nama yang sama dapat dibedakan. Pilihan dipetakan ke identitas wilayah lengkap, bukan dipisah dari teks label.
- Pilih saran untuk filter tepat. Ketik teks dan Enter untuk pencarian sebagian nama kelurahan/kecamatan. Hapus pilihan untuk mengembalikan semua wilayah.
- Pencarian bebas memakai teks literal; karakter regex tidak diinterpretasikan. Filter kota/tahun/profil tetap dikombinasikan dengan hasil pencarian; hasil kosong diberi penjelasan.
- Saran disaring di browser tanpa permintaan ke server per ketukan; debounce tambahan tidak diperlukan. Tidak ada panggilan geocoding atau pengiriman nama wilayah ke layanan lain.

## Analisis data

Lokasi: Klasterisasi → pilih algoritma → Analisis data. Data mencakup seluruh hasil model final pada dataset aktif. Filter peta hanya memengaruhi peta/tabel hasil, bukan grafik analisis.

| Tampilan | Perhitungan dan kegunaan |
| --- | --- |
| Korelasi | Heatmap Pearson 9 × 9, angka dua desimal, warna −1 sampai +1; memakai rata-rata persentase asli antarperiode per kelurahan. Indikator konstan/pasangan valid <3 menghasilkan sel kosong. |
| Distribusi | Sembilan histogram, KDE bila variasi cukup, dan boxplot. Tabel menyajikan data valid, nilai hilang, minimum, median, rata-rata, maksimum, dan jumlah kandidat pencilan di luar 1,5 × IQR. |
| Antar klaster | Boxplot indikator terpilih berdasarkan label model; jumlah anggota dicantumkan. Panel tambahan menampilkan heatmap rata-rata sembilan persentase per klaster. |
| Jumlah & pemisahan | Diagram jumlah dan proporsi kelurahan per klaster, serta scatter dua komponen utama PCA. PCA memakai sembilan Z-score agregasi masukan model dengan pencocokan label berdasarkan kota+kecamatan+kelurahan. Persentase variasi dijelaskan di sumbu. |

Seluruh gambar memiliki judul, sumbu, skala/legenda sesuai jenisnya, penjelasan, serta unduhan PNG 160 dpi. PNG memudahkan penggunaan kembali di laporan. Gambar diperkecil responsif pada layar; file unduhan mempertahankan ukuran aslinya.

Fungsi grafik mengubah nilai nonnumerik/tak hingga menjadi kosong dan mengabaikannya tanpa mengubah masukan model. Validasi CSV yang sudah ada tetap menolak unggahan kosong/tidak numerik. KDE tidak dijalankan pada indikator konstan; PCA yang tidak dapat dibentuk diberi penjelasan. Warna grafik kelompok mewakili nomor klaster; warna titik peta tetap mewakili interpretasi kerawanan.

PCA hanya proyeksi pendukung: tidak mengganti label, penentuan K, atau metrik. Hubungan korelasi bukan bukti sebab-akibat; kandidat pencilan tidak otomatis merupakan data salah.

## Kinerja dan kompatibilitas

Cache model tetap berdasarkan isi CSV dan versi pipeline, maksimum 8 dataset selama 1 jam. Cache PNG terpisah berdasarkan jenis grafik, isi data/model, dan indikator, maksimum 24 entri selama 1 jam. Hanya tab/analisis yang terbuka dirender. Matplotlib memakai backend Agg tanpa jendela dan lock untuk akses antarsesi; figure selalu ditutup setelah disimpan. Aset geografis dibaca sekali per proses. Pergantian filter atau grafik tidak melatih ulang model pada dataset yang sama.

## Library utama yang digunakan

| Library dan versi | Status | Peran/fitur yang benar-benar dipakai | Alasan pemilihan |
| --- | --- | --- | --- |
| Streamlit 1.66.0 | Tersedia | Navigasi, widget autocomplete native, tab malas, tabel, gambar, unduhan, session state, cache, AppTest | Mempertahankan arsitektur Python dan interaksi keyboard tanpa komponen tambahan. |
| pandas 2.3.3 | Tersedia | Pembacaan CSV, validasi tipe, groupby/agregasi per tahun/kelurahan, filter wilayah, korelasi, ringkasan klaster | Operasi tabel konsisten dengan pipeline penelitian. |
| NumPy 1.26.4 | Tersedia | Array masukan model, nilai finite/NaN, koordinat dan variasi PCA | Dasar komputasi numerik yang kompatibel dengan versi model. |
| scikit-learn 1.6.1 | Tersedia; penggunaan diperluas | StandardScaler, KMeans, AgglomerativeClustering Ward, tiga metrik, PCA dua komponen | Metode dan skor penelitian tetap, ditambah proyeksi deterministik dari data yang sama. |
| spectral-bridges 1.3.0 | Tersedia | SpectralBridges asli dengan parameter penelitian | Menjaga reproduksi eksperimen; tidak mengganti metode dengan algoritma lain. |
| faiss-cpu 1.15.1 | Tersedia | Indeks L2 dan pengelompokan internal Spectral Bridges; satu thread | Dependensi metode asli untuk pencarian jarak dan efisiensi. |
| SciPy 1.15.3 | Tersedia | Laplacian graf/BLAS dalam Spectral Bridges; statistik KDE melalui Seaborn | Mendukung perhitungan ilmiah yang dipakai library model dan distribusi. |
| threadpoolctl 3.7.0 | Tersedia | Membatasi thread komputasi model | Menghindari perebutan sumber daya numerik pada aplikasi lokal. |
| Altair 6.3.0 | Tersedia | Donut profil, distribusi kota, centroid, kurva metrik, perbandingan indikator interaktif | Mempertahankan chart interaktif dengan tooltip yang sudah ada. |
| PyDeck 0.9.3 | Tersedia; penggunaan diperluas | GeoJsonLayer, TextLayer, ScatterplotLayer, basemap Voyager, tooltip, pan/zoom, elevasi | Menggabungkan geografi asli dan titik kerawanan dengan renderer peta yang sudah digunakan. |
| PyArrow 19.0.1 | Tersedia | Serialisasi tabel pandas untuk tampilan Streamlit | Jalur tabel Streamlit yang kompatibel dengan NumPy 1.26. |
| Matplotlib 3.10.9 | Baru | Figure/subplot, anotasi, sumbu/legenda, backend Agg, ekspor PNG | Grafik ilmiah yang dapat diunduh dan digunakan dalam laporan. |
| Seaborn 0.13.2 | Baru | heatmap anotasi, histogram+KDE, boxplot, scatter plot | Visual statistik konsisten di atas Matplotlib dengan API pandas. |
| Shapely 2.1.2 | Baru, penyiapan aset | Validasi, union wilayah, simplify dengan topologi, titik label di dalam poligon | Menyiapkan batas lokal kecil tanpa menambah GeoPandas/Fiona pada aplikasi. Tidak dipanggil saat interaksi pengguna. |
| pytest 8.4.2 | Tersedia, pengembangan | Regresi 81 metrik, data/saran/label PCA, struktur lapisan peta, render grafik, AppTest | Memeriksa fitur baru sekaligus melindungi hasil penelitian sebelumnya. |

Tidak ada library JavaScript baru. Python standard library digunakan untuk berkas JSON/GeoJSON, hash cache, ZIP/CSV/PNG download, dan pengambilan sumber batas publik ketika membangun ulang aset.

## Hasil verifikasi

Seluruh **39 pengujian lulus** pada lingkungan proyek. Cakupan mencakup validasi dan agregasi data, regresi **81 nilai metrik PROMPT 02**, tiga model dan navigasi/unggahan, saran wilayah dari dataset aktif, filter literal tanpa membedakan kapital, label PCA saat urutan baris berubah, jumlah/struktur batas asli, urutan lapisan titik di atas batas, render enam jenis grafik, indikator konstan/nonangka, serta pergantian analisis tanpa pelatihan ulang model. Statistik dan grafik diuji memakai dataset penelitian asli.

Pemeriksaan browser lokal memastikan basemap geografis dan batas tampil, saran “aNgKe” menghasilkan wilayah yang sesuai, pemilihan mouse membatasi hasil ke Angke, dan pemilihan keyboard pada Dataset membatasi hasil ke Cempaka Baru. Tata letak gambar distribusi juga diperiksa secara visual. PNG dapat diunduh dari setiap grafik untuk pembacaan beresolusi penuh.
