# Panduan pengembangan dan struktur proyek

Panduan ini menjelaskan struktur aktif. Dokumen PROMPT/revisi lainnya merupakan riwayat pengembangan; tangkapan layar lama tidak selalu mencerminkan antarmuka terbaru.

## Konvensi

- Modul Python memakai `snake_case.py`; fungsi/variabel memakai `snake_case`, kelas memakai `PascalCase`, konstanta memakai `UPPER_CASE`.
- Nama halaman mengikuti navigasi Indonesia: `beranda`, `dataset`, `klasterisasi`, `faq`, `tentang`. URL halaman tetap sama.
- Nama modul teknis mengikuti konvensi Inggris yang sudah digunakan proyek, misalnya `analysis`, `state`, `reports`, dan `evaluation_charts`.
- File pengujian dinamai berdasarkan tanggung jawab, bukan nomor permintaan pengembangan.
- `2425.csv`, nama kolom CSV, nama file dalam laporan ZIP, `PROMPT.md`, dan peluncur tetap dipertahankan demi kompatibilitas.
- Jangan memasukkan lingkungan Python, cache, rahasia, atau hasil eksekusi sementara ke version control.

## Peta kode: bagian mana yang perlu diedit?

| Keperluan | Lokasi | Tanggung jawab |
| --- | --- | --- |
| Navigasi, judul tab browser, sidebar | `app.py` | Titik masuk dan penanganan kesalahan dataset |
| Isi halaman | `app_pages/` | Komposisi halaman; bukan perhitungan model |
| Validasi CSV dan praproses | `firewatch/analysis.py` | `read_dataset`, `validate_dataset`, `prepare_data` |
| Model dan evaluasi numerik | `firewatch/analysis.py` | `fit_labels`, `evaluate`, `choose_k`, `run_method`, `rank_models`, `run_analysis` |
| Dataset aktif/cache | `firewatch/state.py` | Inisialisasi sesi, unggahan/reset, cache model/gambar |
| Bentuk grafik evaluasi | `firewatch/evaluation_charts.py` | Metadata tiga metrik, data Silhouette Plot final, kurva kandidat dan penanda final |
| Panel evaluasi di Streamlit | `firewatch/evaluation_ui.py` | Keterangan, grafik, dan tabel kandidat |
| Peta/donut/profil indikator | `firewatch/charts.py` | Grafik Altair umum dan PyDeck |
| Analisis statistik dan ekspor PNG | `firewatch/eda.py` | Korelasi, distribusi, boxplot indikator per klaster, Silhouette Plot, ringkasan dan PCA |
| Tabel hasil, filter, rincian kelurahan | `firewatch/ui.py` | Komponen Streamlit bersama dan tab hasil model |
| CSV dan laporan ZIP | `firewatch/reports.py` | `csv_bytes`, `report_zip`; format ekspor tidak diubah |
| Interpretasi/audit AHC | `firewatch/profiles.py` | Pemetaan karakteristik dan label tampilan AHC yang sudah ada |
| Warna klaster | `firewatch/palette.py` | Satu warna konsisten per nomor klaster |
| Saran/pencarian wilayah | `firewatch/regions.py` | Identitas wilayah dan filter literal |
| Batas geografis lokal | `firewatch/geography.py`, `assets/boundaries/` | Pembacaan aset batas, bukan fitur model |
| Tema/logo/ilustrasi | `.streamlit/config.toml`, `assets/` | Desain dan aset aktif |
| Pembuatan ulang batas | `scripts/prepare_boundaries.py` | Perintah pengembangan, bukan bagian startup |
| Bukti tampilan historis | `docs/screenshots/` | Semua 14 PNG dokumentasi dikelompokkan, tidak dihapus |

`firewatch.ui` tetap menyediakan impor `csv_bytes`/`report_zip`, dan `firewatch.charts` tetap menyediakan `metric_curve` untuk kompatibilitas. Implementasinya hanya ada satu di modul khusus; bukan salinan kode.

## Aliran data dan sumber grafik

```text
2425.csv / unggahan tervalidasi
  → state.dataset_bytes → read_dataset → prepare_data
  → run_method: fit_labels + evaluate untuk tiap kandidat K
  → choose_k → model final dihitung ulang → evaluate label final
  → ModelResult.trials / ModelResult.metrics
  → rank_models → AnalysisResult.ranking
  → tabel, kartu, grafik, ekspor
```

### Lokasi grafik evaluasi

1. **Klasterisasi → Bandingkan performa ketiga algoritma**: expander ini hanya memuat tabel perbandingan metrik resmi (Silhouette, DBI, CHI, rata-rata peringkat). Grafik diagnostik lama pada expander sudah dihapus; nilai numerik dan tabel tetap menjadi sumber resmi.
2. **Klasterisasi → kartu metrik tiap algoritma → tombol Silhouette Plot**: tombol berada tepat di bawah nilai Silhouette Score dan membuka panel visualisasi dengan pilihan algoritma. `silhouette_analysis` menghitung `silhouette_samples` dari sembilan Z-score dan label final algoritma terpilih. `eda.render_silhouette_plot` menggambar **satu** Silhouette Plot gabungan seluruh klaster: warna berbeda per klaster dari palet aplikasi melalui `matplotlib.cm`, label klaster aktual pada sumbu Y, Silhouette Coefficient pada sumbu X, serta garis putus-putus pada rata-rata yang sama dengan `model.metrics["silhouette"]` dan kartu. Setiap pilihan hanya memakai anggota algoritma tersebut.
3. **Klasterisasi → pilih algoritma → Evaluasi & pemilihan K**: tiga grafik garis/titik dengan nilai kandidat K sebenarnya dan judul berisi nama algoritma. Lingkaran merah menunjukkan K terpilih, wajik hijau menunjukkan metrik model final. Grafik dibuat selebar panel agar label sembilan kandidat tidak berdesakan. Kandidat gagal tidak diberi nilai nol dan garis tidak menghubungkan celah kandidat.
4. **Klasterisasi → Analisis data → Distribusi**: boxplot kelompok indikator kerawanan memakai persentase aktual dan label klaster final algoritma yang dipilih melalui dropdown. Sumbu X berisi nama indikator, sumbu Y berisi nilai persentase, warna berbeda per klaster, dan legenda memuat jumlah anggota. Kotak menampilkan Q1–Q3, garis median, whisker 1,5 × IQR, dan pencilan. Pilihan algoritma tidak mengubah model, tab, jumlah klaster, atau nilai evaluasi.

Nilai kandidat berasal dari `ModelResult.trials`; nilai final berasal dari `ModelResult.metrics`. Keduanya dibedakan karena pipeline memang menghitung ulang model final. Jangan mengganti salah satunya agar terlihat sama. Penanda final sama dengan kartu ringkasan, tabel perbandingan, dan `metodologi.json`. Label/tooltip ditampilkan empat desimal, sedangkan koordinat grafik dan ekspor tetap memakai presisi data asli. Silhouette dan CHI lebih tinggi lebih baik; DBI lebih rendah lebih baik. Perbandingan menilai kualitas klaster, bukan akurasi prediksi kebakaran.

Silhouette Plot dan boxplot indikator memakai seluruh anggota model, bukan hasil filter peta pada tab **Peta & kelurahan**. Warna klaster mengikuti nomor klaster aktual. Fungsi visualisasi hanya membaca `PreparedData` dan `ModelResult`; tidak ada pemanggilan `run_method` atau perubahan `trials`, `metrics`, maupun `villages`.

Interaksi grafik memakai cache model yang ada. Filter peta hanya membatasi tampilan wilayah, tidak memodelkan ulang atau mengubah metrik.

## Perapihan yang aman

- `app_pages/about.py` dipindah menjadi `app_pages/tentang.py`; navigasi dan pengujian diperbarui, URL tetap `/tentang`.
- `tests/test_prompt03.py` dipindah menjadi `tests/test_visualizations_and_regions.py`; cakupan tes lama dipertahankan.
- Implementasi ekspor dan evaluasi dipisah berdasarkan tanggung jawab. Algoritma, parameter, standardisasi, centroid, pemilihan K, ranking, serta label risiko tidak diubah.
- Sembilan PNG di root dan lima PNG di `docs/` dipindah ke `docs/screenshots/`; tautan dokumentasi diperbarui. Isi gambar dipertahankan dan diverifikasi SHA-256.
- Audit hash tidak menemukan file duplikat identik dalam kode/aset/dokumentasi/pengujian. Tidak ada sumber, konfigurasi, dataset, dependensi, atau aset aktif yang dihapus. File inventaris sementara yang dibuat saat audit dibuang.
- `.venv_old/` dikecualikan dari version control tetapi **tidak dihapus**: folder tersebut lingkungan lama, bukan kode aplikasi, dan mungkin masih dibutuhkan konfigurasi IDE pengguna. Aplikasi menggunakan `.venv/`. `.runtime/` juga dipertahankan karena menyimpan sumber GeoJSON yang dibutuhkan saat membangun ulang aset tanpa unduhan, selain log/audit lokal.

## Menjalankan dan menguji

Gunakan `run_app.bat` seperti sebelumnya. Untuk pengujian, dari root proyek:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Pengujian evaluasi khusus:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_evaluation_charts.py -q
```

Tes membaca nilai pada objek grafik dan payload Arrow yang benar-benar dikirim Streamlit, lalu membandingkannya dengan tabel/model dan perhitungan ulang tiga metrik dari label final. Cakupannya termasuk tiga algoritma, dataset unggahan, nilai negatif/nol, kandidat tidak lengkap, nilai kandidat/final yang berbeda, serta interaksi tanpa melatih ulang model. Tes lama tetap memeriksa seluruh halaman, unggah/filter/reset, peta/profil, laporan ZIP, dan 81 nilai referensi penelitian.

## Hasil verifikasi perapihan

Verifikasi dilakukan pada 28 Oktober 2026 dengan Python 3.12.2 di lingkungan `.venv` proyek. Dependensi pengujian dipasang dari `requirements-dev.txt`; tidak ada perubahan daftar atau versi dependensi aplikasi.

- **76 tes lulus**: 60 tes yang sudah ada dan 16 tes evaluasi. Regresi seluruh 81 nilai referensi eksperimen tetap lulus.
- Tes evaluasi memeriksa koefisien Silhouette setiap kelurahan dan rata-ratanya terhadap `model.metrics["silhouette"]`; satu Silhouette Plot gabungan seluruh klaster untuk masing-masing algoritma; boxplot indikator menurut label klaster final; serta payload grafik kandidat/final yang benar-benar dikirim ke browser untuk ketiga algoritma. Penjagaan nilai rata-rata memastikan garis putus-putus grafik sama dengan kartu dan tabel.
- Perbandingan langsung dengan hasil sebelum refaktor menunjukkan masukan Z-score, hasil agregasi, setiap skor kandidat/final, K, peringkat, anggota klaster, centroid, dan interpretasi **identik persis**. Durasi pemodelan dikecualikan karena bergantung pada waktu eksekusi.
- Hash 12 file sumber/data/aset yang dilindungi tetap sama, termasuk `firewatch/analysis.py`, `2425.csv`, `PROMPT.md`, dan seluruh aset aktif.
- Keutuhan 14 PNG setelah dipindah diverifikasi melalui SHA-256. Tidak ada duplikat identik yang perlu dihapus. Seluruh tautan Markdown lokal dan sintaks Python diperiksa.
- `pip check`: **No broken requirements found**.
- Server Streamlit dijalankan pada port lokal sementara; kesehatan `/_stcore/health` menghasilkan `ok`, dan `/`, `/dataset`, `/klasterisasi`, `/faq`, `/tentang` menghasilkan HTTP 200. Server pengujian dihentikan setelah pemeriksaan; peluncur tetap menggunakan port 8501 seperti sebelumnya.
- HTTP memeriksa ketersediaan kerangka aplikasi, sedangkan AppTest mengeksekusi halaman dan interaksi: navigasi, unggah valid/tidak valid, reset, filter, hasil kelurahan, profil, peta, analisis, evaluasi, dan unduhan. Payload Arrow grafik dibaca kembali untuk memeriksa nilai yang benar-benar dikirim ke antarmuka.
- Terdapat 39 `PendingDeprecationWarning` dari integrasi Seaborn/Matplotlib mengenai argumen `vert`; peringatan yang sama sudah muncul pada pengujian awal dan tidak menyebabkan kegagalan. Versi library tidak diubah agar kompatibilitas model tetap terjaga.

### Nilai final dataset bawaan

Angka berikut hanya catatan hasil uji yang dihitung dari dataset asli, **bukan sumber data grafik**. Aplikasi selalu mengambil nilai dari hasil dataset aktif.

| Algoritma | K | Silhouette ↑ | DBI ↓ | CHI ↑ |
| --- | ---: | ---: | ---: | ---: |
| K-Means | 3 | 0.3500 | 0.9426 | 107.8559 |
| AHC | 3 | 0.2495 | 1.0020 | 94.9169 |
| Spectral Bridges | 2 | 0.6455 | 1.3079 | 38.2610 |

### Batas verifikasi

Pemeriksaan piksel/tata letak dengan browser grafis tidak dilakukan pada sesi ini. Grafik sudah lolos validasi skema Altair dan pengujian render/serialisasi Streamlit, tetapi pembacaan visual pada perangkat/ukuran layar pengguna tetap dapat diperiksa dengan membuka aplikasi. Latar peta dan font eksternal masih memerlukan internet seperti sebelumnya. Folder kerja tidak memiliki repository Git, sehingga audit perubahan memakai inventaris, hash, dan salinan hasil numerik sebelum/sesudah, bukan `git diff`.

Log lokal disimpan di `.runtime/`: `verification.stdout.log`, `organization_audit.json`, `duplicate_audit.json`, `final_tests.stdout.log`, `verified_tests.stdout.log`, serta `smoke_check.stdout.log`. Folder ini diabaikan version control dan bukan dependensi baru aplikasi.