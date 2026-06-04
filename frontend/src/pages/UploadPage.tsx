import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Typography, Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import client from '../api/client';

const { Dragger } = Upload;
const { Title, Text } = Typography;

export default function UploadPage() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    const formData = new FormData();
    formData.append('files', file as File);

    try {
      setUploading(true);
      const response = await client.post('/v1/projects', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onSuccess?.(response.data);
      message.success('Upload successful!');
      navigate(`/projects/${response.data.id}`);
    } catch (err) {
      onError?.(err as Error);
      message.error('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleChange: UploadProps['onChange'] = ({ fileList: newFileList }) => {
    setFileList(newFileList);
  };

  return (
    <Card style={{ maxWidth: 600, margin: '60px auto', textAlign: 'center' }}>
      <Title level={2}>Upload Smart Contracts</Title>
      <Text type="secondary">
        Upload your Solidity files (.sol, .zip, .tar.gz) for analysis
      </Text>
      <Dragger
        accept=".sol,.zip,.tar.gz"
        multiple
        fileList={fileList}
        onChange={handleChange}
        customRequest={handleUpload}
        disabled={uploading}
        style={{ marginTop: 24 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">Click or drag files to this area to upload</p>
        <p className="ant-upload-hint">
          Supports .sol, .zip, and .tar.gz files
        </p>
      </Dragger>
    </Card>
  );
}
