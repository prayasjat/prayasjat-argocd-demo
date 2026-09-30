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

                        echo "Docker client:"
                        docker --version

                        echo "Docker server:"
                        docker version

                        echo "Building image..."
                        docker build -t nginx-demo:${BUILD_NUMBER} .
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
                        docker run --rm nginx-demo:${BUILD_NUMBER} nginx -t

                        echo "Testing application files..."
                        docker run --rm nginx-demo:${BUILD_NUMBER} \
                          sh -c 'test -f /usr/share/nginx/html/index.html'

                        echo "Container test passed"
                    '''
                }
            }
        }
    }

    post {
        always {
            container('docker') {
                sh '''
                    docker image rm nginx-demo:${BUILD_NUMBER} 2>/dev/null || true
                '''
            }
        }

        success {
            echo 'CI pipeline completed successfully.'
        }

        failure {
            echo 'CI pipeline failed.'
        }
    }
}
