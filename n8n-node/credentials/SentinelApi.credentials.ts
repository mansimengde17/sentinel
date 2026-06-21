import {
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class SentinelApi implements ICredentialType {
	name = 'sentinelApi';
	displayName = 'Sentinel API';
	properties: INodeProperties[] = [
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			default: '',
			typeOptions: {
				password: true,
			},
			required: true,
		},
		{
			displayName: 'Backend URL',
			name: 'backendUrl',
			type: 'string',
			default: 'http://localhost:8000',
			description: 'Base URL of the Sentinel backend service',
			required: true,
		},
	];
}
