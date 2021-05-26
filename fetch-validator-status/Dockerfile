FROM bcgovimages/von-image:next-1

ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ADD networks.json .
ADD *.py ./

ENTRYPOINT ["bash", "-c", "python fetch_status.py $@", "--"]