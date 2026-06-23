FROM public.ecr.aws/docker/library/fedora:44
ENV PYTHONPATH="/local_libs"

#Update system
RUN dnf update -y

# Install system dependencies
RUN dnf install -y python python-pip python3-devel pdal PDAL-devel gdal gdal-devel uv g++ git

# Download stac factory to local directory
RUN mkdir /local_libs
WORKDIR /local_libs
RUN git clone https://github.com/TNRIS/stac_factory.git

# Setup workspace for entrypoint
WORKDIR /stac_generator
RUN uv init .
RUN uv venv

# Install stac factory locally, maintaining libraries directory root.
RUN uv pip install -e /local_libs/stac_factory