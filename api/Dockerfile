FROM python:3.8-slim-buster

#ENV CELERY_BROKER_URL redis://redis:6379/0
#ENV CELERY_RESULT_BACKEND redis://redis:6379/0
#ENV C_FORCE_ROOT true

ARG SECRET_KEY
ARG DATABASE_URL
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_BUCKET
ARG AWS_REGION
ARG CLOUDFRONT_DOMAIN

ENV SECRET_KEY ${SECRET_KEY?secretkeynotset}
ENV DATABASE_URL ${DATABASE_URL?envdberror}
ENV AWS_ACCESS_KEY_ID ${AWS_ACCESS_KEY_ID?accesskeyiderror}
ENV AWS_SECRET_ACCESS_KEY ${AWS_SECRET_ACCESS_KEY?ACCESSKEYERROR}
ENV AWS_BUCKET ${AWS_BUCKET?awsbucketwrrorenv}
ENV AWS_REGION ${AWS_REGION?awsregionerror}
ENV CLOUDFRONT_DOMAIN ${CLOUDFRONT_DOMAIN?CFERROR}
ENV HOST 0.0.0.0
ENV PORT 5001
ENV DEBUG false

COPY . .
WORKDIR /project_flask_basic

# install requirements
RUN pip install -r requirements.txt

# expose the app port
EXPOSE 5001

RUN pip install gunicorn

# run the app server in production with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "3", "flask_hello:app","--preload"]