export AWS_PAGER=""

mkdir package;

# Copy the files to the package directory
cp -r ./function/* package
cp -r requirements.txt package

# Install the dependencies
cd package && pip install -r requirements.txt -t ./

# Zip the package
zip -r ../package.zip ./

# Remove the package directory
cd .. && rm -rf package

# Deploy the package
aws lambda update-function-code --region us-east-2 --function-name mcafee-bot --zip-file fileb://package.zip
latest_Version=`aws lambda list-versions-by-function --region us-east-2 --function-name mcafee-bot \
  --page-size=99 \
  --query "max_by(Versions, &to_number(to_number(Version) || '0'))" | jq -r .Version`

echo "Latest Version: $latest_Version"
new_version=$((latest_Version + 1))
aws lambda publish-version --region us-east-2 --function-name mcafee-bot --description $new_version


echo "New Version Published: $new_version"

# Remove the package
rm package.zip

# Update lambda environment variables
#value=`cat secrets.json`
#echo "$value"
#aws lambda update-function-configuration --region us-east-2 --function-name yap-bot --environment "Variables={VERSION=$new_version}"
