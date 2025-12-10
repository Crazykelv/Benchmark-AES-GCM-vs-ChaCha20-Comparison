# Benchmarking AES-GCM vs ChaCha20-Poly1305 pada Protokol TLS 1.3

## Gambaran Umum

Progran ini menyediakan sebuah alat benchmark berbasis Python yang
digunakan untuk mengukur dan membandingkan kinerja dua algoritma
*Authenticated Encryption with Associated Data* (AEAD) yang digunakan
dalam TLS 1.3, yaitu **AES-GCM** dan **ChaCha20-Poly1305**. Alat ini
menghitung waktu enkripsi, penggunaan CPU, serta waktu eksekusi total
pada berbagai ukuran file dan perangkat keras.

Tujuan utama benchmark ini adalah untuk menjawab: - Algoritma mana yang
lebih cepat pada berbagai ukuran file? - Bagaimana pengaruh akselerasi
perangkat keras (seperti AES-NI) terhadap performa AES-GCM? - Apakah
ChaCha20-Poly1305 tetap kompetitif di perangkat modern tanpa akselerasi
hardware?

## Algoritma yang Digunakan

### AES-GCM

AES-GCM (*Advanced Encryption Standard -- Galois/Counter Mode*) adalah
salah satu algoritma enkripsi yang paling banyak digunakan pada protokol
keamanan, termasuk TLS 1.2 dan TLS 1.3.

**Karakteristik:** - Menggunakan cipher AES dalam mode counter yang
digabungkan dengan GHASH. - Sangat cepat pada CPU yang memiliki dukungan
instruksi AES-NI. - Sering menjadi pilihan default pada perangkat
laptop/desktop modern.

### ChaCha20-Poly1305

ChaCha20-Poly1305 adalah cipher modern berbasis stream cipher, dipadukan
dengan fungsi autentikasi Poly1305.

**Karakteristik:** - Dirancang untuk cepat tanpa memerlukan akselerasi
perangkat keras. - Efisien pada perangkat mobile, IoT, embedded system,
dan CPU tanpa AES-NI. - Banyak digunakan di TLS 1.3, QUIC, dan HTTP/3.

## Deskripsi Program

Script utama, `benchmark.py`, melakukan langkah-langkah berikut:

1.  Memuat daftar file uji (*dummy files*) dengan berbagai ukuran.
2.  Melakukan proses enkripsi menggunakan:
    -   AES-GCM
    -   ChaCha20-Poly1305
3.  Mengukur:
    -   *Wall time* (waktu total proses)
    -   *CPU time* (waktu komputasi murni)
4.  Mengulang setiap percobaan beberapa kali untuk akurasi statistik.
5.  Menghasilkan output berupa:
    -   `raw_results.csv` → log detail setiap iterasi
    -   `summary_avg.csv` → ringkasan rata-rata dan standar deviasi
    -   `time_avg.png` → grafik waktu eksekusi
    -   `cpu_avg.png` → grafik penggunaan CPU

Script juga menghapus file ciphertext sementara, kecuali jika pengguna
menambahkan flag `--keep-outputs`.

## Kebutuhan Sistem

Instal dependensi berikut:

    pip install cryptography pandas matplotlib

## Cara Menggunakan

### 1. Siapkan File Dummy

Buat file untuk pengujian, misalnya:

-   10MB\
-   100MB\
-   500MB\
-   1GB

Contoh pembuatan file di Windows:

    fsutil file createnew tes_100MB.bin 104857600

### 2. Jalankan Benchmark

Contoh penggunaan dasar:

    python benchmark.py --files tes_10MB.bin tes_100MB.bin tes_500MB.bin tes_1GB.bin

Menjalankan dengan jumlah iterasi berbeda:

    python benchmark.py --files *.bin --iters 15

Menyimpan hasil pada direktori khusus:

    python benchmark.py --files *.bin --outdir hasil_benchmark

Menyimpan file ciphertext:

    python benchmark.py --files *.bin --keep-outputs

## Hasil Output

### `raw_results.csv`

Berisi data semua iterasi: - Ukuran file - Algoritma yang dipakai -
*Wall time* - *CPU time* - Lokasi file ciphertext sementara

### `summary_avg.csv`

Berisi statistik ringkasan: - Rata-rata waktu enkripsi - Standar
deviasi - Dikelompokkan berdasarkan algoritma dan ukuran file

### `time_avg.png`

Grafik batang untuk perbandingan *wall time* antara AES-GCM dan
ChaCha20-Poly1305.

### `cpu_avg.png`

Grafik batang untuk perbandingan *CPU time*.

## Catatan Tambahan

-   AES-GCM dapat berjalan sangat cepat pada CPU dengan AES-NI.
-   ChaCha20-Poly1305 biasanya unggul pada CPU low-end atau perangkat
    tanpa hardware acceleration.
-   Script membaca file secara penuh ke RAM; jika ingin mode streaming,
    kode perlu dimodifikasi secara khusus.

## Lisensi

Program ini dibuat untuk keperluan UAS Mata Kuliah Kriptografi.

## Developer

Fahri Aminuddin Abdillah
Faiq Pataya Zain
Riskyta
