pipeline {

    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: docker
      image: docker:cli
      command:
        - cat
      tty: true
      volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock

  volumes:
    - name: docker-sock
      hostPath:
        path: /var/run/docker.sock
        type: Socket
'''
        }
    }

    environment {
        IMAGE = "prayasjat/nginx-demo:${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Validate') {
            steps {
                sh '''
                    set -e

                    test -f Dockerfile
                    test -f app.py
                    test -f requirements.txt
                    test -f k8s/deployment.yaml
                    test -f k8s/service.yaml
                    test -f k8s/jaeger.yaml

                    echo "Required files are present"
                '''
            }
        }

        stage('Docker Build') {
            steps {
                container('docker') {
                    sh '''
                        set -e

                        echo "Building ${IMAGE}"

                        docker build \
                            --provenance=false \
                            --sbom=false \
                            -t "${IMAGE}" .

                        echo "Docker build completed."
                    '''
                }
            }
        }

        stage('Container Test') {
            steps {
                container('docker') {
                    sh '''
                        set -e

                        CONTAINER="booking-test-${BUILD_NUMBER}"

                        echo "Starting test container..."

                        docker run -d \
                            --name "${CONTAINER}" \
                            "${IMAGE}"

                        trap 'docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true' EXIT

                        echo "Waiting for application..."
                        sleep 5

                        echo "Testing /health..."

                        docker exec "${CONTAINER}" \
                            python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8080/health'); print(r.read().decode())"

                        echo "Testing /metrics..."

                        docker exec "${CONTAINER}" \
                            python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8080/metrics'); print('metrics endpoint OK:', r.status)"

                        echo "Container tests passed."
                    '''
                }
            }
        }

        stage('Docker Push') {
            steps {
                container('docker') {
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'dockerhub-creds',
                            usernameVariable: 'DOCKER_USER',
                            passwordVariable: 'DOCKER_PASS'
                        )
                    ]) {
                        sh '''
                            set -e

                            echo "$DOCKER_PASS" | docker login \
                                -u "$DOCKER_USER" \
                                --password-stdin

                            echo "Pushing ${IMAGE}..."

                            timeout 10m docker push \
                                --platform linux/amd64 \
                                "${IMAGE}"

                            docker logout

                            echo "Docker image pushed successfully."
                        '''
                    }
                }
            }
        }

        stage('GitOps Update') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GIT_USER',
                        passwordVariable: 'GIT_TOKEN'
                    )
                ]) {
                    sh '''
                        set -e

                        echo "Updating Kubernetes image to ${IMAGE}"

                        sed -i -E \
                            "s#(^[[:space:]]*image: ).*#\\1${IMAGE}#" \
                            k8s/deployment.yaml

                        echo "Images in deployment.yaml:"
                        grep "image:" k8s/deployment.yaml

                        git config user.name "jenkins"
                        git config user.email "jenkins@localhost"

                        git add k8s/deployment.yaml

                        if git diff --cached --quiet; then
                            echo "No manifest change detected."
                            exit 0
                        fi

                        git commit \
                            -m "Update application image to ${IMAGE}"

                        git push \
                            "https://${GIT_USER}:${GIT_TOKEN}@github.com/prayasjat/prayasjat-argocd-demo.git" \
                            HEAD:main

                        echo "GitOps update completed successfully."
                    '''
                }
            }
        }
    }

    post {

        always {
            container('docker') {
                sh '''
                    docker image rm "${IMAGE}" 2>/dev/null || true
                '''
            }
        }

        success {
            echo 'CI + Docker + GitOps pipeline completed successfully.'
        }

        failure {
            echo 'Pipeline failed.'
        }
    }
}
EOF
