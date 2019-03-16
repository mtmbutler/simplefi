# start from an official image
FROM python:3.6

# arbitrary location choice: you can change the directory
RUN mkdir -p /opt/services/simplefi/src
WORKDIR /opt/services/simplefi/src

# install our two dependencies
COPY requirements.txt /opt/services/simplefi/src
RUN pip install -r requirements.txt

# copy our project code
COPY . /opt/services/simplefi/src

# expose the port 8000
EXPOSE 8000

# define the default command to run when starting the container
CMD ["gunicorn", "--chdir", "simplefi", "--bind", ":8000", "simplefi.wsgi:application"]

