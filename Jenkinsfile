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
                        docker build -t "${IMAGE}" .
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
                            docker push "${IMAGE}"

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
