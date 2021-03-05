#!/usr/bin/python
from pathlib import Path
import urllib.request
import numpy as np
import matplotlib.pyplot as plt
from tifffile import imread, imwrite 
import picoquant_tttr as pq

def main():
    for filename in ('1_dye_solution.ptu',
                     '2_a_few_yeast.ptu',
                     '3_many_yeast.ptu'):
        ptu_filename = Path.cwd() / filename
        image_filename = ptu_filename.with_suffix('.tif')
        figure_filename = ptu_filename.with_suffix('.png')

        # Raw data is stored on Zenodo:
        download_if_needed(filename)

        # Read the raw data header:
        tags = pq.parse_tttr_header(ptu_filename, verbose=False)

        # An aesthetic choice that affects histogram generation:
        t_pix_per_bin = 40 # Smaller timebins for less-ugly histograms            
        t_bin_width_ns = (t_pix_per_bin *
                          tags['MeasDesc_Resolution']['values'][0]
                          * 1e9)
        print("Time bin width:", t_bin_width_ns, "ns")

        # We want to deal with binned data:
        if image_filename.is_file(): # Binned data already computed, just reload
            images = imread(image_filename)
        else: # We've got work to do
            frames = pq.generate_picoharp_t3_frames(
                ptu_filename, tags, verbose=True)
            images = []
            for i, f in enumerate(frames):
                if i > 5: # Only parse the first N frames
                    break
                print("Parsing frame ", i, '... ', sep='', end='')
                parsed_frame = pq.parse_picoharp_t3_frame(
                    records=f,
                    tags=tags,
                    verbose=True,
                    show_plot=False)
                im = pq.parsed_frame_to_histogram(
                    parsed_frame,
                    x_pix_per_bin=1,
                    y_pix_per_bin=1,
                    t_pix_per_bin=t_pix_per_bin)
                images.append(im)
                print("done.")
            images = np.array(images)
            imwrite(image_filename, images.astype('float32'), imagej=True)
        print("Photons binned into images:", images.shape, images.dtype)

        plt.figure(figsize=(8, 4))
        # 2D image of the sample
        ax1 = plt.axes((0, 0, 0.5, 1))
        im = images.sum(axis=(0, 1, 2))
        ax1.imshow(im, cmap=plt.cm.gray, interpolation='nearest')
        # 1D fluorescence lifetime histogram
        ax2 = plt.axes((0.6, 0.15, 0.39, 0.8))
        t_ns = np.arange(images.shape[1]) * t_bin_width_ns
        lifetime_curve = images.sum(axis=(0, 2, 3, 4))
        plt.semilogy(t_ns, lifetime_curve, '.-')
        plt.xlabel("Time (ns)\nTimebin width: %i ps"%(t_bin_width_ns*1e3))
        plt.ylabel("Photoelectrons per time bin")
        plt.xlim(t_ns[0],
                 t_ns[np.max(np.nonzero(lifetime_curve))] + t_bin_width_ns)
        plt.grid('on')
        plt.savefig(figure_filename)

    plt.show()

def download_if_needed(filename):
    if Path(filename).is_file():
        return None
    print("\n  The data file:")
    print(filename)
    print("  ...isn't where we expect it.\n")
    print(" * * Let's try to download it from Zenodo.")
    url="https://zenodo.org/record/4585872/files/" + filename
    u = urllib.request.urlopen(url)
    file_size = int(u.getheader("Content-Length"))
    block_size = 8192
    while block_size * 80 < file_size:
        block_size *= 2
    bar_size = max(1, int(0.5 * (file_size / block_size - 12)))

    print("    Downloading from:")
    print(url)
    print("    Downloading to:")
    print(filename)
    print("    File size: %0.2f MB"%(file_size/2**20))
    print("\nDownloading might take a while, so here's a progress bar:")
    print('0%', "-"*bar_size, '50%', "-"*bar_size, '100%')
    with open(filename, 'wb') as f:
        while True:
            buffer = u.read(block_size)
            if not buffer:
                break
            f.write(buffer)
            print('|', sep='', end='')
    print("\nDone downloading.\n")
    assert Path(filename).is_file()
    return None

main()
