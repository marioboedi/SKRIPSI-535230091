# Penyeragaman legenda dan label — aplikasi 1.2.3

Komposisi Profil Kerawanan di Beranda serta Sebaran Klaster/Profil di Klasterisasi menggunakan komponen legenda yang sama. Urutannya adalah label berwarna di kiri, jumlah kelurahan tebal, lalu persentase dengan satu angka desimal di kanan. Legenda berada di luar diagram dan dapat membungkus pada layar sempit. Warna label menggunakan warna diagram/peta yang persis sama; warna nomor klaster tetap dipertahankan saat filter berubah.

Kedua diagram menggunakan ukuran lingkaran, angka total di tengah, dan penjelasan irisan kecil yang sama. Jumlah dan persentase dihitung dari data tampilan aktif. Tiga klaster AHC tetap ditampilkan terpisah meskipun dua klaster mempunyai profil kerawanan yang sama. Tidak ada pembesaran irisan atau perubahan proporsi.

Kategori **Risiko Rendah** ditetapkan dari satu konstanta backend, digunakan pada hasil model, urutan kategori, warna, peta, diagram, legenda, tooltip, filter, tabel, rincian kelurahan, FAQ, dan hasil CSV/ZIP. Warna hijau tetap sama. Aturan kedua indeks centroid ≤0,5 tetap sama. Versi label disertakan pada kunci cache dan kontrol filter agar kosakata lama tidak muncul kembali; versi pipeline numerik tetap 1.1.0.

Seluruh **44 tes lulus**, termasuk regresi 81 metrik penelitian dan konsistensi label di filter, peta, tabel, diagram, serta unduhan. Perbandingan langsung hasil sebelum dan sesudah revisi menunjukkan masukan Z-score, setiap anggota klaster, nilai centroid, K, skor tiap kandidat, dan skor final ketiga algoritma **identik**, dengan pengecualian nama kategori yang memang diganti. Durasi eksekusi tidak dibandingkan karena bergantung pada perangkat.

Dataset 2425.csv tidak diubah. SHA-256 tetap `9cc540c37b870a70cbb56b8fd57ce9e233908de5589b1b04f3602fbedcbc7647`.

## Pembaruan 1.2.4 — Sebaran Profil AHC

Khusus AHC, mode **Profil kerawanan → Sebaran profil** sekarang memakai label klaster final sebagai pengelompokan irisan. Tiga klaster bawaan ditampilkan terpisah: 1, 128, dan 138 kelurahan, dengan persentase 0,4%, 47,9%, dan 51,7%. Profil setiap klaster ditulis di bawah labelnya; klaster 2 dan 3 tetap berprofil Risiko Rendah dan tidak digabung. Warna peta mengikuti nomor klaster agar sesuai dengan diagram.

Filter tetap bekerja: jika hanya sebagian klaster masuk filter, keterangan menjelaskan jumlah klaster yang tampil dari total K model. Mode profil K-Means dan Spectral Bridges tetap memakai kategori kerawanan semula. Tidak ada perubahan kode algoritma, parameter, ambang kategori, data, atau pemilihan K. Seluruh **46 tes lulus**, termasuk pemeriksaan khusus perilaku AHC dan regresi kedua algoritma lain.

## Pembaruan 1.2.5 — Legenda kategori AHC tanpa duplikasi

Penyebab label Risiko Rendah berulang adalah legenda AHC dibentuk per klaster, lalu interpretasi dicetak untuk setiap klaster. Klaster 2 dan 3 memang berbeda, tetapi keduanya mempunyai interpretasi Risiko Rendah. Sumber data dan pemetaan kategori benar; pengulangan berasal dari cara legenda disusun.

Sebaran Profil AHC kini memakai komponen legenda kategori yang sama dengan Beranda, K-Means, dan Spectral Bridges. Setiap kategori muncul satu kali dengan urutan, warna, format teks, jumlah, dan persentase yang seragam. Jumlah dihitung langsung dari kelurahan pada hasil filter aktif. Pada data bawaan: Gas **1 kelurahan (0,4%)**, Risiko Rendah **266 kelurahan (99,6%)**, Listrik & gas dan Kelistrikan masing-masing **0 kelurahan (0,0%)**. Jika hanya Risiko Rendah dipilih, legenda menjadi **266 kelurahan (100,0%)**.

Tiga klaster AHC tetap terpisah pada data diagram melalui nomor klaster sebagai detail: **1, 128, dan 138 kelurahan**. Batas irisan dan tooltip mempertahankan rincian tiap klaster; warna diagram dan peta mengikuti kategori risiko. Mode Klaster masih menggunakan warna berbeda per nomor. Hasil model, perhitungan, parameter, ambang kategori, data masukan, dan pemilihan K tidak diubah. Versi pipeline tetap 1.1.0.

Seluruh **47 tes lulus**. Pengujian mencakup label legenda yang unik, jumlah dan persentase sebelum/sesudah filter, tiga irisan AHC yang tetap terpisah, kesesuaian warna, keutuhan data hasil, serta regresi kedua algoritma lainnya dan 81 nilai metrik penelitian. Pemeriksaan langsung di browser lokal memastikan tiga arc AHC tetap terbentuk dan empat baris legenda tidak bertumpuk pada tampilan selebar 416 piksel. Bukti tampilan: [legenda AHC](screenshots/ahc-legenda-risiko-unik.png).

## Pembaruan 1.2.6 — Satu sumber tiga klaster AHC untuk kedua diagram

Pemeriksaan alur data menunjukkan `run_method` memilih K=3, kemudian `build_profiles` menghasilkan tiga nomor klaster final beserta centroid dan interpretasinya. Seluruh 267 kelurahan mempunyai label final tersebut. Tampilan sebelumnya masih mewarnai Sebaran Profil berdasarkan dua kategori risiko dan merangkum legendanya menjadi dua kategori berisi data. Akibatnya, klaster 2 dan 3 yang sama-sama Risiko Rendah terlihat menyatu meskipun data irisan masih terpisah.

Kedua tampilan kini menggunakan satu agregasi backend `cluster_membership_summary` berdasarkan kolom `klaster` dari hasil model final. Kategori risiko menjadi atribut setiap klaster, bukan kunci pengelompokan anggota. Ringkasan yang sama diteruskan ke satu fungsi diagram dan ke legenda; jumlah anggota, persentase, nomor, serta warna ketiga klaster identik pada Sebaran Klaster dan Sebaran Profil. Ringkasan menolak label kosong atau interpretasi yang tidak konsisten di dalam satu klaster.

Pada dataset bawaan, keduanya menampilkan:

| Klaster final | Kategori dari centroid | Jumlah kelurahan | Persentase |
| --- | --- | ---: | ---: |
| 1 | Dominan Bahaya Gas | 1 | 0,4% |
| 2 | Risiko Rendah | 128 | 47,9% |
| 3 | Risiko Rendah | 138 | 51,7% |

Legenda Sebaran Profil menampilkan kategori Gas satu kali di atas klaster 1, dan Risiko Rendah satu kali di atas klaster 2 serta 3. Setiap klaster memiliki warna, jumlah, dan persentase sendiri. Tidak ada penambahan kategori risiko ketiga atau penggantian label model. Peta AHC pada kedua mode mengikuti warna nomor klaster. Mode profil K-Means dan Spectral Bridges mempertahankan perilaku sebelumnya.

Filter tetap mempertahankan nomor klaster model. Contohnya, memilih Risiko Rendah menampilkan klaster 2 dan 3 sebanyak 128 dan 138 kelurahan dengan proporsi 48,1% dan 51,9% terhadap 266 hasil filter. Menghapus filter mengembalikan ketiga klaster. Perhitungan standardisasi, pemilihan K, algoritma, centroid, dan ambang risiko tidak diubah; versi pipeline tetap 1.1.0.

Pengujian membandingkan spesifikasi dan data terkiriman kedua diagram, seluruh hasil per kelurahan, jumlah anggota dari profil centroid, proporsi sebelum/sesudah filter, serta urutan baris acak dan nomor klaster berbeda. Regresi algoritma lain dan 81 nilai metrik penelitian tetap disertakan.

Seluruh **49 tes lulus**. Verifikasi browser lokal juga membaca tiga irisan nyata pada Sebaran Klaster dan tiga irisan nyata pada Sebaran Profil, dengan anggota 1/128/138 dan proporsi 0,4%/47,9%/51,7% yang sama. Legenda pada layar selebar 416 piksel menampilkan kategori Gas satu kali dan Risiko Rendah satu kali, disertai tiga rincian klaster. Bukti tampilan: [Sebaran Profil AHC tiga klaster](screenshots/ahc-konsisten-3-klaster.png).

## Pembaruan 1.3.0 — Sebaran klaster dan profil terpadu

Pilihan tampilan Klaster / Profil kerawanan dihapus dari halaman Klasterisasi. Ketiga algoritma sekarang menggunakan satu **Sebaran klaster dan profil**, dengan satu irisan untuk setiap label klaster model final. Setiap keterangan memuat label klaster berwarna, jumlah kelurahan, persentase, dan profil kerawanan dari centroid klaster tersebut. Keterangan diurutkan berdasarkan nomor klaster agar mudah dibandingkan. Klaster yang memiliki kategori sama tetap memperoleh rincian sendiri, sesuai permintaan informasi per klaster.

Sumber data tetap `cluster_membership_summary` yang menghitung anggota dari kolom `klaster` dan mengambil interpretasi yang sudah dipetakan dari centroid. Hasil ringkasan yang sama diteruskan ke diagram dan keterangannya untuk semua algoritma. Nomor klaster menentukan warna peta, irisan, dan label. Tooltip tetap menampilkan nomor, interpretasi, jumlah, dan proporsi. Tidak ada cabang khusus tampilan profil AHC maupun penggabungan anggota berdasarkan kategori risiko.

Pada data bawaan, AHC tetap memiliki tiga klaster beranggotakan 1/128/138 kelurahan, K-Means tetap tiga klaster, dan Spectral Bridges tetap dua klaster. Filter menyesuaikan jumlah dan penyebut persentase terhadap seluruh kelurahan yang sedang ditampilkan, seperti sebelumnya; penjelasan penyebut dicantumkan pada ringkasan. Menghapus filter mengembalikan seluruh klaster. Pemilihan algoritma, pencarian, filter, peta/elevasi/batas kelurahan, rincian centroid, evaluasi, analisis data, unggahan, dan unduhan tetap tersedia. Beranda tetap memakai diagram kategori risiko semula.

Kode perhitungan dan pemilihan K, data, centroid, ambang risiko, dan parameter tidak diubah. Versi pipeline numerik tetap 1.1.0 dan versi label tetap 2. Pengujian ketiga algoritma membaca kembali data Arrow yang benar-benar dikirim ke diagram dan membandingkannya dengan kelompok anggota pada tabel hasil, lalu mencocokkan setiap label, profil, jumlah, persentase, dan warna. Pengujian juga memeriksa sesi dengan pilihan tampilan lama, filter AHC tanpa pelatihan ulang, pemulihan seluruh klaster setelah filter dihapus, dan dataset unggahan.

Seluruh **50 tes lulus**, termasuk regresi 81 nilai metrik penelitian dan fitur lain. Pemeriksaan langsung di browser memastikan pilihan tampilan lama sudah hilang, ketiga algoritma menggunakan format terpadu, dan setiap label klaster terhubung dengan profil serta jumlah yang sesuai. Pada layar selebar 319 piksel, ketiga keterangan AHC terbaca tanpa bertumpuk. Bukti tampilan: [sebaran klaster dan profil terpadu](screenshots/klaster-dan-profil-terpadu.png).
