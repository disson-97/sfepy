#!/usr/bin/env python
import sys
sys.path.append( '.' )
import os
import tempfile
import glob
from optparse import OptionParser

import matplotlib.image as image

import sfepy
from sfepy.base.base import get_default, ordered_iteritems, output, Struct
from sfepy.base.ioutils import ensure_path, locate_files, remove_files

omits = [
    'linear_elastic_mM.py',
]

def _get_fig_filename(ebase, images_dir):
    fig_base = os.path.splitext(ebase)[0].replace(os.path.sep, '-')
    fig_filename = os.path.join(images_dir, fig_base + '.png')

    return fig_base, fig_filename

def _make_sphinx_path(path, relative=False):
    if relative:
        aux = path.replace(sfepy.data_dir, '')
        prefix = ('..' + os.path.sep) * aux.count(os.path.sep)
        sphinx_path = prefix[:-1] + aux

    else:
        sphinx_path = path.replace(sfepy.data_dir, '/..')

    return sphinx_path

def generate_images(images_dir, examples_dir):
    """
    Generate images from results of running examples found in
    `examples_dir` directory.

    The generated images are stored to `images_dir`,
    """
    from sfepy.applications import pde_solve
    from sfepy.postprocess import Viewer
    from sfepy.postprocess.utils import mlab

    prefix = output.prefix

    output_dir = tempfile.mkdtemp()
    trunk = os.path.join(output_dir, 'result')
    options = Struct(output_filename_trunk=trunk,
                     output_format='vtk',
                     save_ebc=False,
                     save_regions=False,
                     save_field_meshes=False,
                     save_regions_as_groups=False,
                     solve_not=False)

    ensure_path(images_dir + os.path.sep)

    view = Viewer('',
                  output_dir=output_dir,
                  offscreen=False)

    for ex_filename in locate_files('*.py', examples_dir):
        base = os.path.basename(ex_filename)
        if base in omits: continue

        output.level = 0
        output.prefix = prefix
        ebase = ex_filename.replace(examples_dir, '')[1:]
        output('trying "%s"...' % ebase)

        try:
            problem, state = pde_solve(ex_filename, options=options)

        except KeyboardInterrupt:
            raise

        except:
            problem = None
            output('***** failed! *****')

        if problem is not None:
            fig_filename = _get_fig_filename(ebase, images_dir)[1]

            if problem.ts_conf is None:
                filename = trunk + '.vtk'

            else:
                suffix = problem.ts.suffix % problem.ts.step
                filename = problem.get_output_name(suffix=suffix)

            output('displaying results from "%s"' % filename)
            output('to "%s"...'
                   % fig_filename.replace(sfepy.data_dir, '')[1:])

            view.filename = filename
            view(scene=view.scene, show=False, is_scalar_bar=True,
                 fig_filename=fig_filename)
            mlab.clf()

            output('...done')

            remove_files(output_dir)

        output('...done')

def generate_thumbnails(thumbnails_dir, images_dir, scale=0.3):
    """
    Generate thumbnails into `thumbnails_dir` corresponding to images in
    `images_dir`.
    """
    ensure_path(thumbnails_dir + os.path.sep)

    output('generating thumbnails...')
    filenames = glob.glob(os.path.join(images_dir, '*.png'))
    for fig_filename in filenames:
        ebase = fig_filename.replace(sfepy.data_dir, '')[1:]
        output('"%s"' % ebase)

        base = os.path.basename(fig_filename)
        thumb_filename = os.path.join(thumbnails_dir, base)

        image.thumbnail(fig_filename, thumb_filename, scale=scale)

    output('...done')

_index = """\
.. _%s-index:

%s examples
%s=========

.. toctree::
    :maxdepth: 2

"""

_include = """\
.. _%s:

%s
%s

.. image:: %s

:download:`source code <%s>`

.. literalinclude:: %s

"""

def generate_rst_files(rst_dir, examples_dir, images_dir):
    """
    Generate Sphinx rst files for examples in `examples_dir` with images
    in `images_dir` and put them into `rst_dir`.
    """
    ensure_path(rst_dir + os.path.sep)

    output('generating rst files...')

    dir_map = {}
    for ex_filename in locate_files('*.py', examples_dir):
        base = os.path.basename(ex_filename)
        if base in omits: continue

        ebase = ex_filename.replace(examples_dir, '')[1:]
        base_dir = os.path.dirname(ebase)

        rst_filename = os.path.basename(ex_filename).replace('.py', '.rst')

        dir_map.setdefault(base_dir, []).append((ex_filename, rst_filename))

    # Main index.
    mfd = open(os.path.join(rst_dir, 'index.rst'), 'w')
    mfd.write(_index % ('sfepy', 'SfePy autogenerated gallery', '=' * 27))

    for dirname, filenames in ordered_iteritems(dir_map):
        full_dirname = os.path.join(rst_dir, dirname)
        ensure_path(full_dirname + os.path.sep)

        # Subdirectory index.
        ifd = open(os.path.join(full_dirname, 'index.rst'), 'w')
        ifd.write(_index % (dirname, dirname, '=' * len(dirname)))

        for ex_filename, rst_filename in filenames:
            full_rst_filename = os.path.join(full_dirname, rst_filename)
            output('"%s"' % full_rst_filename.replace(rst_dir, '')[1:])
            rst_filename_ns = rst_filename.replace('.rst', '')
            ebase = ex_filename.replace(examples_dir, '')[1:]

            fig_base, fig_filename = _get_fig_filename(ebase, images_dir)

            ifd.write('    %s\n' % rst_filename_ns)

            rst_fig_filename = _make_sphinx_path(fig_filename)
            rst_ex_filename = _make_sphinx_path(ex_filename)
            src_ex_filename = _make_sphinx_path(ex_filename, True)

            # Example rst file.
            fd = open(full_rst_filename, 'w')
            fd.write(_include % (fig_base, ebase, '=' * len(ebase),
                                 rst_fig_filename,
                                 src_ex_filename, rst_ex_filename))
            fd.close()

        ifd.close()

        mfd.write('    %s/index\n' % dirname)

    mfd.close()

    output('...done')

usage = """%prog [options]

Generate the images and rst files for gallery of SfePy examples.
"""
help = {
    'output_filename' :
    'output file name [default: %default]',
    'examples_dir' :
    'directory containing examples [default: %default]',
    'images_dir' :
    'directory where to store gallery images [default: gallery/images]',
    'no_images' :
    'do not (re)generate images and thumbnails',
}

def main():
    parser = OptionParser(usage=usage, version='%prog')
    parser.add_option('-e', '--examples-dir', metavar='directory',
                      action='store', dest='examples_dir',
                      default='examples', help=help['examples_dir'])
    parser.add_option('-i', '--images-dir', metavar='directory',
                      action='store', dest='images_dir',
                      default=None, help=help['images_dir'])
    parser.add_option('-n', '--no-images',
                      action='store_true', dest='no_images',
                      default = False, help = help['no_images'])
    parser.add_option('-o', '--output', metavar='output_filename',
                      action='store', dest='output_filename',
                      default='gallery/gallery.html',
                      help=help['output_filename'])
    (options, args) = parser.parse_args()

    examples_dir = os.path.realpath(options.examples_dir)
    gallery_dir = os.path.dirname(os.path.realpath(options.output_filename))

    images_dir = get_default(options.images_dir,
                             os.path.join(gallery_dir, 'images'))

    thumbnails_dir = os.path.join(images_dir, 'thumbnails')
    rst_dir = os.path.join(gallery_dir, 'examples')

    if not options.no_images:
        generate_images(images_dir, examples_dir)
        generate_thumbnails(thumbnails_dir, images_dir)

    generate_rst_files(rst_dir, examples_dir, images_dir)

if __name__ == '__main__':
    main()
