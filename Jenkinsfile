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
                    test -f index.html
                    test -f k8s/deployment.yaml
                    test -f k8s/service.yaml
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
                        docker build --provenance=false --sbom=false -t "${IMAGE}" .
                    '''
                }
            }
        }

        stage('Container Test') {
            steps {
                container('docker') {
                    sh '''
                        set -e

                        echo "Testing nginx configuration..."
                        docker run --rm "${IMAGE}" nginx -t

                        echo "Testing application files..."
                        docker run --rm "${IMAGE}" \
                          sh -c 'test -f /usr/share/nginx/html/index.html'

                        echo "Container test passed"
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
                '''
            }
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
            echo 'CI + Docker Registry pipeline completed successfully.'
        }

        failure {
            echo 'Pipeline failed.'
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

                sed -i -E "s#(^[[:space:]]*image: ).*#\\1${IMAGE}#" k8s/deployment.yaml

                git config user.name "jenkins"
                git config user.email "jenkins@localhost"

                git add k8s/deployment.yaml
                git commit -m "Update nginx image to ${IMAGE}"

                git remote set-url origin "https://${GIT_USER}:${GIT_TOKEN}@github.com/prayasjat/prayasjat-argocd-demo.git"
                git push origin HEAD:main
            '''
        }
    }
}
