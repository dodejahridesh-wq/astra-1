from .organism import AstraOrganism

if __name__ == '__main__':
    result=AstraOrganism().run('validate the Astra-1 sandbox organism loop')
    print('verified:', result['verified'])
    for event in result['trace']:
        print(f"[{event['stage']}] {event['detail']}")
