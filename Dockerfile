FROM theharpia/microservice_template_core:v2.2.26

WORKDIR /code

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
RUN python setup.py install

CMD ["harp-actions"]
