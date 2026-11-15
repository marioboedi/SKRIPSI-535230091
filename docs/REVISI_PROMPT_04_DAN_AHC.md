# Revisi PROMPT 04 dan visualisasi AHC

Aplikasi 1.2.2 menggunakan pipeline penelitian 1.1.0. Parameter, label model, centroid, pemilihan K, serta skor evaluasi tidak berubah.

## Revisi PROMPT 04

- Halaman Dataset menyediakan satu tombol **Data Terbaru** menuju URL Google Drive yang sebelumnya digunakan. Tombol unduh lokal yang duplikat dihapus. Ekspor data tampilan tetap tersedia melalui menu CSV pada tabel; unggah, filter, dan reset dataset dipertahankan.
- Kontrol Kepulauan Seribu di Beranda dan Klasterisasi dihapus, termasuk parameter tampilan khususnya. Enam kelurahan Kepulauan Seribu tetap berada dalam data, model, hasil tabel, dan peta. Filter wilayah tetap dapat menelusurinya; cakupan di luar daratan awal otomatis dipusatkan pada hasil filter.
- Donut tidak lagi menggunakan jarak tetap antaririsan maupun ujung membulat yang dapat menutup irisan satu kelurahan. Sudut irisan tetap berdasarkan jumlah sebenarnya. Semua empat kategori profil tercantum di legenda, termasuk nilai nol, dengan jumlah dan persentase. Kategori berproporsi <1% mendapat keterangan tambahan.
- Pada Tentang Aplikasi, hanya kalimat tentang perbandingan Silhouette, DBI, dan CHI di bagian Dosen Pembimbing yang dihapus. Nama pembimbing dan konten lainnya dipertahankan.

## Penyebab perbedaan tampilan AHC

Model AHC pada dataset bawaan memang mempunyai **tiga klaster**. Diagram sebelumnya menghitung anggota per **interpretasi kerawanan**, sehingga dua klaster dengan interpretasi sama digabung menjadi satu kategori visual.

| Label model final | Jumlah kelurahan | Persentase | Profil kerawanan |
| --- | ---: | ---: | --- |
| Klaster 1 | 1 | 0,4% | Dominan Bahaya Gas |
| Klaster 2 | 128 | 47,9% | Risiko Rendah |
| Klaster 3 | 138 | 51,7% | Risiko Rendah |
| Total | 267 | 100,0% | Dua kategori profil terisi |

Di Klasterisasi, pilihan **Warna dan sebaran** sekarang mengatur peta dan diagram secara bersamaan:

- **Klaster** menjadi pilihan awal. Peta memakai warna berbeda per label model; diagram menampilkan irisan, nomor klaster, jumlah, serta persentase dari label final. Dengan demikian AHC ditampilkan sebagai tiga warna dan tiga irisan.
- **Profil kerawanan** tetap tersedia untuk interpretasi centroid. Dalam mode ini, AHC mempunyai dua kategori terisi: satu kelurahan Dominan Bahaya Gas dan 266 Risiko Rendah. Jumlah klaster model tetap tiga.
- Warna suatu nomor klaster tetap sama ketika filter berubah. Jika hanya sebagian klaster masuk filter, keterangan menampilkan jumlah klaster yang terlihat dari total klaster model.
- Tooltip peta dan diagram tetap menyediakan nomor klaster serta profilnya. Warna klaster juga konsisten dengan grafik analisis data.

## Verifikasi

Seluruh **43 pengujian lulus**, mencakup semua halaman, unggah/filter/reset, akses tombol Google Drive, penghapusan kontrol, proporsi irisan kecil, data Kepulauan Seribu, kesesuaian tiga warna peta dan legenda AHC, pergantian mode profil, serta regresi seluruh **81 nilai metrik PROMPT 02**. Pengujian mode profil memastikan tabel tetap menyimpan tiga label klaster meskipun peta mempunyai dua warna interpretasi.

Pemeriksaan browser lokal memastikan legenda Beranda menampilkan satu kelurahan Gas sebagai **0,4%** dengan irisan asli yang tetap tipis dan terbaca melalui legenda. Server aplikasi berjalan pada port 8501.

Pemeriksaan akhir AHC di browser memastikan diagram menampilkan tiga irisan dengan legenda **1, 128, dan 138 kelurahan**, serta keterangan **3 dari 3 klaster**. Ruang untuk legenda disediakan terpisah dari lingkaran agar irisan dan teks tidak bertumpuk pada layar kecil. Dua pengujian khusus AHC juga lulus setelah perapian diagram.
